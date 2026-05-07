from datetime import timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Conta, Lancamento, LancamentoTransacao, OfxImport,
    StatusConciliacao, Transacao, Usuario,
)
from app.services.ofx_service import importar_ofx
from app.api.deps import get_current_user


router = APIRouter(prefix="/api/conciliacao", tags=["conciliacao"])


def _transacao_to_dict(t: Transacao) -> dict:
    return {
        "id": t.id,
        "descricao": t.descricao,
        "tipo": t.tipo,
        "valor": float(t.valor),
        "data_pagamento": t.data_pagamento.isoformat(),
        "conta_id": t.conta_id,
        "conta_nome": t.conta.nome if t.conta else None,
        "forma_pagamento": t.forma_pagamento,
        "status_conciliacao": t.status_conciliacao,
    }


@router.get("/pendentes")
def pendentes(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transacoes = (
        db.query(Transacao)
        .filter(Transacao.status_conciliacao == StatusConciliacao.pendente)
        .order_by(Transacao.data_pagamento.desc())
        .all()
    )
    return [_transacao_to_dict(t) for t in transacoes]


@router.post("/upload")
async def upload_ofx(
    conta_id: int = Form(...),
    arquivo: UploadFile = File(...),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conta = db.query(Conta).filter(Conta.id == conta_id).first()
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    conteudo = await arquivo.read()
    try:
        resultado = importar_ofx(conteudo, arquivo.filename, conta, current_user, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"importados": resultado["importadas"], "duplicados": resultado["duplicatas"]}


@router.post("/ignorar/{transacao_id}")
def ignorar_transacao(
    transacao_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.query(Transacao).filter(Transacao.id == transacao_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    t.status_conciliacao = StatusConciliacao.ignorado
    db.commit()
    return {"ok": True}


class CriarLancamentoBody(BaseModel):
    descricao: str
    categoria_id: Optional[int] = None


@router.post("/criar-lancamento/{transacao_id}")
def criar_lancamento_da_transacao(
    transacao_id: int,
    body: CriarLancamentoBody,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.query(Transacao).filter(Transacao.id == transacao_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transação não encontrada")

    lancamento = Lancamento(
        descricao=body.descricao,
        tipo=t.tipo,
        valor_total=t.valor,
        data_competencia=t.data_pagamento,
        categoria_id=body.categoria_id or None,
        usuario_id=current_user.id,
    )
    db.add(lancamento)
    db.flush()

    vinculo = LancamentoTransacao(
        lancamento_id=lancamento.id,
        transacao_id=transacao_id,
        valor_vinculado=t.valor,
    )
    db.add(vinculo)
    t.status_conciliacao = StatusConciliacao.conciliado
    db.commit()
    return {"ok": True}


@router.get("/historico")
def historico(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    imports = db.query(OfxImport).order_by(OfxImport.importado_em.desc()).limit(20).all()
    return [
        {
            "id": imp.id,
            "conta_nome": imp.conta.nome if imp.conta else None,
            "arquivo_nome": imp.arquivo_nome,
            "total_registros": imp.total_registros,
            "importado_em": imp.importado_em.isoformat() if imp.importado_em else None,
        }
        for imp in imports
    ]
