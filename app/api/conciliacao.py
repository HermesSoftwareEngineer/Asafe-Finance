from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Conta, Lancamento, OfxImport, OfxTransaction,
    StatusConciliacao, StatusOfxTransaction, TipoLancamento,
)
from app.api.deps import get_current_user
from app.services import ofx_service


router = APIRouter(prefix="/api/conciliacao", tags=["conciliacao"])

MAX_OFX_SIZE = 5 * 1024 * 1024  # 5 MB


def _ofx_tx_to_dict(t: OfxTransaction, matches: list[dict] | None = None) -> dict:
    return {
        "id": t.id,
        "conta_id": t.conta_id,
        "data": t.data.isoformat(),
        "valor": float(t.valor),
        "tipo": t.tipo,
        "descricao": t.descricao,
        "ofx_transaction_id": t.ofx_transaction_id,
        "status": t.status,
        "lancamento_id": t.lancamento_id,
        "sugestoes": [
            {
                "lancamento_id": m["lancamento"].id,
                "descricao": m["lancamento"].descricao,
                "valor_total": float(m["lancamento"].valor_total),
                "data": m["lancamento"].data.isoformat() if m["lancamento"].data else None,
                "score": m["score"],
            }
            for m in (matches or [])
        ],
    }


# ─── UPLOAD OFX ───────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_ofx(
    conta_id: int = Form(...),
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Validação de conta
    conta = db.query(Conta).filter(Conta.id == conta_id, Conta.ativo == True).first()
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    # Validação do arquivo
    if file.content_type and "ofx" not in file.content_type and "xml" not in file.content_type:
        # content_type nem sempre é confiável — verificamos pelo nome
        pass
    filename = file.filename or "upload.ofx"
    if not filename.lower().endswith((".ofx", ".qfx")):
        raise HTTPException(status_code=400, detail="Apenas arquivos .OFX ou .QFX são aceitos")

    content = await file.read()
    if len(content) > MAX_OFX_SIZE:
        raise HTTPException(status_code=400, detail="Arquivo excede o limite de 5 MB")
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    try:
        resultado = ofx_service.importar_ofx(db, content, conta_id, current_user.id, filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {
        **resultado,
        "conta_nome": conta.nome,
        "mensagem": f"{resultado['novos_registros']} transação(ões) importada(s). {resultado['duplicatas_ignoradas']} duplicata(s) ignorada(s).",
    }


# ─── LISTAR PENDENTES ─────────────────────────────────────────────────────────

@router.get("/pendentes")
def listar_pendentes(
    conta_id: Optional[int] = None,
    com_sugestoes: bool = True,
    page: int = Query(1, ge=1),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    PER_PAGE = 30
    q = db.query(OfxTransaction).filter(OfxTransaction.status == StatusOfxTransaction.pendente)
    if conta_id:
        q = q.filter(OfxTransaction.conta_id == conta_id)
    q = q.order_by(OfxTransaction.data.desc())

    total = q.count()
    txs = q.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()

    items = []
    for t in txs:
        matches = ofx_service.buscar_matches(db, t) if com_sugestoes else []
        items.append(_ofx_tx_to_dict(t, matches))

    return {"items": items, "total": total, "page": page, "per_page": PER_PAGE}


# ─── VINCULAR A LANÇAMENTO EXISTENTE ──────────────────────────────────────────

class VincularBody(BaseModel):
    lancamento_id: int


@router.put("/vincular/{ofx_id}")
def vincular_lancamento(
    ofx_id: int,
    body: VincularBody,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ofx_t = db.query(OfxTransaction).filter(OfxTransaction.id == ofx_id).first()
    if not ofx_t:
        raise HTTPException(status_code=404, detail="Transação OFX não encontrada")
    if ofx_t.status != StatusOfxTransaction.pendente:
        raise HTTPException(status_code=400, detail="Transação OFX já processada")

    lancamento = db.query(Lancamento).filter(Lancamento.id == body.lancamento_id).first()
    if not lancamento:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    if lancamento.conta_id != ofx_t.conta_id:
        raise HTTPException(status_code=400, detail="Lançamento pertence a uma conta diferente da transação OFX")
    if lancamento.status != "pago":
        raise HTTPException(status_code=400, detail="Só é possível vincular lançamentos com status 'pago'")

    # Vincular
    ofx_t.status = StatusOfxTransaction.conciliado
    ofx_t.lancamento_id = lancamento.id
    lancamento.status_conciliacao = StatusConciliacao.conciliado
    lancamento.ofx_transaction_id = ofx_t.ofx_transaction_id

    db.commit()
    return {
        "ok": True,
        "lancamento_id": lancamento.id,
        "mensagem": f"Lançamento '{lancamento.descricao}' conciliado com sucesso.",
    }


# ─── CRIAR LANÇAMENTO A PARTIR DO OFX ────────────────────────────────────────

class CriarLancamentoOfxBody(BaseModel):
    categoria_id: Optional[int] = None
    centro_custo_id: Optional[int] = None
    observacao: Optional[str] = None
    observacao: Optional[str] = None


@router.put("/criar-lancamento/{ofx_id}")
def criar_lancamento_ofx(
    ofx_id: int,
    body: CriarLancamentoOfxBody,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ofx_t = db.query(OfxTransaction).filter(OfxTransaction.id == ofx_id).first()
    if not ofx_t:
        raise HTTPException(status_code=404, detail="Transação OFX não encontrada")
    if ofx_t.status != StatusOfxTransaction.pendente:
        raise HTTPException(status_code=400, detail="Transação OFX já processada")

    lancamento = Lancamento(
        descricao=ofx_t.descricao,
        tipo=ofx_t.tipo,
        valor_total=ofx_t.valor,
        data=ofx_t.data,
        status="pago",
        categoria_id=body.categoria_id or None,
        centro_custo_id=body.centro_custo_id or None,
        conta_id=ofx_t.conta_id,
        observacao=body.observacao,
        usuario_id=current_user.id,
        status_conciliacao=StatusConciliacao.conciliado,
        ofx_transaction_id=ofx_t.ofx_transaction_id,
    )
    db.add(lancamento)
    db.flush()

    ofx_t.status = StatusOfxTransaction.conciliado
    ofx_t.lancamento_id = lancamento.id

    db.commit()
    db.refresh(lancamento)

    return {
        "ok": True,
        "lancamento_id": lancamento.id,
        "mensagem": f"Lançamento '{lancamento.descricao}' criado e conciliado.",
    }


# ─── IGNORAR TRANSAÇÃO OFX ────────────────────────────────────────────────────

@router.put("/ignorar/{ofx_id}")
def ignorar_transacao(
    ofx_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ofx_t = db.query(OfxTransaction).filter(OfxTransaction.id == ofx_id).first()
    if not ofx_t:
        raise HTTPException(status_code=404, detail="Transação OFX não encontrada")
    if ofx_t.status == StatusOfxTransaction.conciliado:
        raise HTTPException(status_code=400, detail="Transação já conciliada — desvincule antes de ignorar")

    ofx_t.status = StatusOfxTransaction.ignorado
    db.commit()
    return {"ok": True, "mensagem": "Transação OFX marcada como ignorada."}


# ─── DESFAZER CONCILIAÇÃO ─────────────────────────────────────────────────────

@router.put("/desvincular/{ofx_id}")
def desvincular(
    ofx_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ofx_t = db.query(OfxTransaction).filter(OfxTransaction.id == ofx_id).first()
    if not ofx_t:
        raise HTTPException(status_code=404, detail="Transação OFX não encontrada")
    if ofx_t.status != StatusOfxTransaction.conciliado:
        raise HTTPException(status_code=400, detail="Transação OFX não está conciliada")

    if ofx_t.lancamento:
        ofx_t.lancamento.status_conciliacao = StatusConciliacao.pendente
        ofx_t.lancamento.ofx_transaction_id = None

    ofx_t.status = StatusOfxTransaction.pendente
    ofx_t.lancamento_id = None
    db.commit()
    return {"ok": True, "mensagem": "Conciliação desfeita."}


# ─── HISTÓRICO DE IMPORTS ─────────────────────────────────────────────────────

@router.get("/historico")
def historico(
    conta_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    PER_PAGE = 20
    q = db.query(OfxImport)
    if conta_id:
        q = q.filter(OfxImport.conta_id == conta_id)
    q = q.order_by(OfxImport.importado_em.desc())

    total = q.count()
    imports = q.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()

    items = []
    for imp in imports:
        conciliados = db.query(func.count(OfxTransaction.id)).filter(
            OfxTransaction.ofx_import_id == imp.id,
            OfxTransaction.status == StatusOfxTransaction.conciliado,
        ).scalar() or 0
        ignorados = db.query(func.count(OfxTransaction.id)).filter(
            OfxTransaction.ofx_import_id == imp.id,
            OfxTransaction.status == StatusOfxTransaction.ignorado,
        ).scalar() or 0
        pendentes = imp.novos_registros - conciliados - ignorados

        items.append({
            "id": imp.id,
            "conta_id": imp.conta_id,
            "conta_nome": imp.conta.nome if imp.conta else None,
            "arquivo_nome": imp.arquivo_nome,
            "data_inicio": imp.data_inicio.isoformat() if imp.data_inicio else None,
            "data_fim": imp.data_fim.isoformat() if imp.data_fim else None,
            "total_registros": imp.total_registros,
            "novos_registros": imp.novos_registros,
            "conciliados": conciliados,
            "ignorados": ignorados,
            "pendentes": max(pendentes, 0),
            "importado_em": imp.importado_em.isoformat() if imp.importado_em else None,
            "importado_por": imp.usuario.nome if imp.usuario else None,
        })

    return {"items": items, "total": total, "page": page, "per_page": PER_PAGE}


# ─── RESUMO DE DIFERENÇAS ─────────────────────────────────────────────────────

@router.get("/diferencas")
def diferencas(
    conta_id: Optional[int] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    hoje = date.today()
    di = data_inicio or hoje.replace(day=1)
    df = data_fim or hoje

    # Lançamentos realizados não conciliados
    q_lanc = db.query(Lancamento).filter(
        Lancamento.status == "pago",
        Lancamento.status_conciliacao == StatusConciliacao.pendente,
        Lancamento.data >= di,
        Lancamento.data <= df,
    )
    if conta_id:
        q_lanc = q_lanc.filter(Lancamento.conta_id == conta_id)
    lancamentos_sem_ofx = q_lanc.all()

    # OFX transactions pendentes no período
    q_ofx = db.query(OfxTransaction).filter(
        OfxTransaction.status == StatusOfxTransaction.pendente,
        OfxTransaction.data >= di,
        OfxTransaction.data <= df,
    )
    if conta_id:
        q_ofx = q_ofx.filter(OfxTransaction.conta_id == conta_id)
    ofx_sem_lancamento = q_ofx.all()

    return {
        "data_inicio": di.isoformat(),
        "data_fim": df.isoformat(),
        "lancamentos_nao_conciliados": [
            {
                "id": l.id,
                "descricao": l.descricao,
                "valor_total": float(l.valor_total),
                "tipo": l.tipo,
                "data": l.data.isoformat(),
                "conta_id": l.conta_id,
            }
            for l in lancamentos_sem_ofx
        ],
        "ofx_sem_lancamento": [
            {
                "id": t.id,
                "descricao": t.descricao,
                "valor": float(t.valor),
                "tipo": t.tipo,
                "data": t.data.isoformat(),
                "conta_id": t.conta_id,
            }
            for t in ofx_sem_lancamento
        ],
        "total_lancamentos_nao_conciliados": len(lancamentos_sem_ofx),
        "total_ofx_sem_lancamento": len(ofx_sem_lancamento),
    }
