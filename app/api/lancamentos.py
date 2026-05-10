from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Lancamento, StatusConciliacao, Usuario
from app.api.deps import get_current_user
from app.services import recorrencia_service


router = APIRouter(prefix="/api/lancamentos", tags=["lancamentos"])

PER_PAGE = 20

STATUS_VALIDOS = {"pago", "a pagar"}
TIPO_RECORRENCIA_VALIDOS = {"unico", "fixo", "parcelado"}
FREQUENCIAS_VALIDAS = {"diaria", "semanal", "quinzenal", "mensal"}


class LancamentoBody(BaseModel):
    descricao: str
    tipo: str
    valor_total: float
    data: str
    status: str = "a pagar"
    conta_id: int
    categoria_id: Optional[int] = None
    centro_custo_id: Optional[int] = None
    observacao: Optional[str] = None
    # Recorrência
    tipo_recorrencia: str = "unico"
    frequencia_recorrencia: Optional[str] = None
    total_parcelas: Optional[int] = None


def _lancamento_to_dict(l: Lancamento) -> dict:
    return {
        "id": l.id,
        "descricao": l.descricao,
        "tipo": l.tipo,
        "valor_total": float(l.valor_total),
        "data": l.data.isoformat(),
        "status": l.status,
        "tipo_recorrencia": l.tipo_recorrencia,
        "frequencia_recorrencia": l.frequencia_recorrencia,
        "total_parcelas": l.total_parcelas,
        "numero_parcela": l.numero_parcela,
        "lancamento_pai_id": l.lancamento_pai_id,
        "status_conciliacao": l.status_conciliacao,
        "ofx_transaction_id": l.ofx_transaction_id,
        "conta_id": l.conta_id,
        "conta_nome": l.conta.nome if l.conta else None,
        "categoria_id": l.categoria_id,
        "categoria_nome": l.categoria.nome if l.categoria else None,
        "categoria_icone": l.categoria.icone if l.categoria else None,
        "centro_custo_id": l.centro_custo_id,
        "centro_custo_nome": l.centro_custo.nome if l.centro_custo else None,
        "observacao": l.observacao,
    }


def _parse_date(value: str, field_name: str = "data") -> date:
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"{field_name} inválida (use YYYY-MM-DD)")


def _validar_body_recorrencia(body: LancamentoBody) -> None:
    if body.tipo_recorrencia not in TIPO_RECORRENCIA_VALIDOS:
        raise HTTPException(status_code=400, detail="tipo_recorrencia deve ser 'unico', 'fixo' ou 'parcelado'")
    if body.tipo_recorrencia in ("fixo", "parcelado"):
        if not body.frequencia_recorrencia:
            raise HTTPException(status_code=400, detail="frequencia_recorrencia é obrigatória para lançamentos fixos e parcelados")
        if body.frequencia_recorrencia not in FREQUENCIAS_VALIDAS:
            raise HTTPException(status_code=400, detail="frequencia_recorrencia deve ser 'diaria', 'semanal', 'quinzenal' ou 'mensal'")
    if body.tipo_recorrencia == "parcelado":
        if not body.total_parcelas or body.total_parcelas < 2:
            raise HTTPException(status_code=400, detail="total_parcelas deve ser >= 2 para lançamentos parcelados")


def _aplicar_status_conciliacao(lancamento: Lancamento, novo_status: str) -> None:
    if novo_status == "pago":
        if lancamento.status_conciliacao not in (StatusConciliacao.conciliado, StatusConciliacao.ignorado):
            lancamento.status_conciliacao = StatusConciliacao.pendente
    else:
        if lancamento.status_conciliacao != StatusConciliacao.conciliado:
            lancamento.status_conciliacao = None


def _descricao_para_lancamento(base_descricao: str, lancamento: Lancamento) -> str:
    if lancamento.tipo_recorrencia == "parcelado" and lancamento.numero_parcela and lancamento.total_parcelas:
        return f"{base_descricao} ({lancamento.numero_parcela}/{lancamento.total_parcelas})"
    return base_descricao


def _atualizar_lancamento_campos(
    lancamento: Lancamento,
    body: LancamentoBody,
    aplicar_data: bool = True,
    atualizar_descricao_parcelas: bool = False,
) -> None:
    lancamento.descricao = _descricao_para_lancamento(body.descricao if atualizar_descricao_parcelas else body.descricao, lancamento)
    lancamento.tipo = body.tipo
    lancamento.valor_total = Decimal(str(body.valor_total))
    if aplicar_data:
        lancamento.data = _parse_date(body.data)
    lancamento.status = body.status
    lancamento.conta_id = body.conta_id
    lancamento.categoria_id = body.categoria_id or None
    lancamento.centro_custo_id = body.centro_custo_id or None
    lancamento.observacao = body.observacao
    _aplicar_status_conciliacao(lancamento, body.status)


# ─── LISTAR ───────────────────────────────────────────────────────────────────

@router.get("")
def listar_lancamentos(
    page: int = Query(1, ge=1),
    tipo: Optional[str] = None,
    status: Optional[str] = None,
    tipo_recorrencia: Optional[str] = None,
    status_conciliacao: Optional[str] = None,
    categoria_id: Optional[int] = None,
    centro_custo_id: Optional[int] = None,
    conta_id: Optional[int] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Lancamento)

    if tipo:
        q = q.filter(Lancamento.tipo == tipo)
    if status:
        q = q.filter(Lancamento.status == status)
    if tipo_recorrencia:
        q = q.filter(Lancamento.tipo_recorrencia == tipo_recorrencia)
    if status_conciliacao:
        q = q.filter(Lancamento.status_conciliacao == status_conciliacao)
    if categoria_id:
        q = q.filter(Lancamento.categoria_id == categoria_id)
    if centro_custo_id:
        q = q.filter(Lancamento.centro_custo_id == centro_custo_id)
    if conta_id:
        q = q.filter(Lancamento.conta_id == conta_id)
    if data_inicio:
        q = q.filter(Lancamento.data >= data_inicio)
    if data_fim:
        q = q.filter(Lancamento.data <= data_fim)

    q = q.order_by(Lancamento.data.desc())
    total = q.count()
    lancamentos = q.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()

    return {
        "items": [_lancamento_to_dict(l) for l in lancamentos],
        "total": total,
        "page": page,
        "per_page": PER_PAGE,
    }


# ─── CRIAR ────────────────────────────────────────────────────────────────────

@router.post("")
def criar_lancamento(
    body: LancamentoBody,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.valor_total <= 0:
        raise HTTPException(status_code=400, detail="O valor deve ser maior que zero")
    if body.status not in STATUS_VALIDOS:
        raise HTTPException(status_code=400, detail="status deve ser 'pago' ou 'a pagar'")
    _validar_body_recorrencia(body)

    lancamento = Lancamento(
        descricao=body.descricao,
        tipo=body.tipo,
        valor_total=Decimal(str(body.valor_total)),
        data=_parse_date(body.data),
        status=body.status,
        tipo_recorrencia=body.tipo_recorrencia,
        frequencia_recorrencia=body.frequencia_recorrencia or None,
        categoria_id=body.categoria_id or None,
        centro_custo_id=body.centro_custo_id or None,
        conta_id=body.conta_id,
        observacao=body.observacao,
        usuario_id=current_user.id,
        status_conciliacao=StatusConciliacao.pendente if body.status == "pago" else None,
    )
    db.add(lancamento)
    db.flush()

    filhos = []
    if body.tipo_recorrencia == "parcelado":
        filhos = recorrencia_service.gerar_parcelas(
            db, lancamento, body.total_parcelas, body.frequencia_recorrencia
        )

    db.commit()
    db.refresh(lancamento)

    if filhos:
        return {
            "total_criados": len(filhos) + 1,
            "lancamentos": [_lancamento_to_dict(lancamento)] + [_lancamento_to_dict(f) for f in filhos],
        }
    return _lancamento_to_dict(lancamento)


# ─── EDITAR ───────────────────────────────────────────────────────────────────

@router.put("/{lancamento_id}")
def editar_lancamento(
    lancamento_id: int,
    body: LancamentoBody,
    scope: str = Query("only", regex="^(only|all|future)$"),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lancamento = db.query(Lancamento).filter(Lancamento.id == lancamento_id).first()
    if not lancamento:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    if body.valor_total <= 0:
        raise HTTPException(status_code=400, detail="O valor deve ser maior que zero")
    if body.status not in STATUS_VALIDOS:
        raise HTTPException(status_code=400, detail="status deve ser 'pago' ou 'a pagar'")

    if scope == "only":
        _atualizar_lancamento_campos(lancamento, body, aplicar_data=True, atualizar_descricao_parcelas=True)
        db.commit()
        db.refresh(lancamento)
        return _lancamento_to_dict(lancamento)

    raiz, serie = recorrencia_service._serie_completa(db, lancamento_id)
    if not serie:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")

    if scope == "all":
        targets = serie
    else:
        targets = [l for l in serie if l.data >= lancamento.data]

    for l in targets:
        aplicar_data = l.id == lancamento.id
        _atualizar_lancamento_campos(l, body, aplicar_data=aplicar_data, atualizar_descricao_parcelas=True)

    db.commit()
    return {
        "updated": [_lancamento_to_dict(l) for l in targets]
    }


# ─── EXCLUIR ──────────────────────────────────────────────────────────────────

@router.delete("/{lancamento_id}")
def excluir_lancamento(
    lancamento_id: int,
    scope: str = Query("only", regex="^(only|all|future)$"),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lancamento = db.query(Lancamento).filter(Lancamento.id == lancamento_id).first()
    if not lancamento:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")

    if scope == "only":
        if lancamento.tipo_recorrencia != "unico" or lancamento.lancamento_pai_id is not None:
            raiz, serie = recorrencia_service._serie_completa(db, lancamento_id)
            if serie and serie[0].id == lancamento.id and len(serie) > 1:
                recorrencia_service.promover_novo_raiz(db, lancamento_id)
        db.delete(lancamento)
        db.commit()
        return {"ok": True, "total_excluidos": 1}

    raiz, serie = recorrencia_service._serie_completa(db, lancamento_id)
    if not serie:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")

    if scope == "all":
        targets = serie
    else:
        targets = [l for l in serie if l.data >= lancamento.data]

    for l in targets:
        db.delete(l)

    db.commit()
    return {"ok": True, "total_excluidos": len(targets)}


# ─── SÉRIE (fixo/parcelado) ───────────────────────────────────────────────────

@router.get("/{lancamento_id}/serie")
def listar_serie(
    lancamento_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todos = recorrencia_service.todos_da_serie(db, lancamento_id)
    if not todos:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    return {
        "total": len(todos),
        "lancamentos": [_lancamento_to_dict(l) for l in todos],
    }


@router.delete("/{lancamento_id}/serie")
def excluir_serie(
    lancamento_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lancamento = db.query(Lancamento).filter(Lancamento.id == lancamento_id).first()
    if not lancamento:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    if lancamento.tipo_recorrencia == "unico":
        raise HTTPException(status_code=400, detail="Use DELETE /{id} para lançamentos únicos")
    total = recorrencia_service.excluir_serie(db, lancamento_id)
    db.commit()
    return {"ok": True, "total_excluidos": total}


@router.post("/{lancamento_id}/gerar-proximo")
def gerar_proximo(
    lancamento_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lancamento = db.query(Lancamento).filter(Lancamento.id == lancamento_id).first()
    if not lancamento:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")

    try:
        proximo = recorrencia_service.gerar_proximo_fixo(db, lancamento_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    db.commit()
    db.refresh(proximo)
    return _lancamento_to_dict(proximo)
