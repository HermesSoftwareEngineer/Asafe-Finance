from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Lancamento, LancamentoTransacao, StatusConciliacao, Transacao, Usuario,
)
from app.api.deps import get_current_user


router = APIRouter(prefix="/api/transacoes", tags=["transacoes"])

PER_PAGE = 20


class TransacaoBody(BaseModel):
    descricao: str
    tipo: str
    valor: float
    data_pagamento: str
    conta_id: int
    forma_pagamento: str

    @field_validator("forma_pagamento", "tipo")
    @classmethod
    def normalizar_lower(cls, v: str) -> str:
        return v.lower()


class VincularBody(BaseModel):
    lancamento_id: int
    valor_vinculado: float


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


@router.get("")
def listar_transacoes(
    page: int = Query(1, ge=1),
    conta_id: Optional[int] = None,
    status_conciliacao: Optional[str] = None,
    forma_pagamento: Optional[str] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Transacao)
    if conta_id:
        q = q.filter(Transacao.conta_id == conta_id)
    if status_conciliacao:
        q = q.filter(Transacao.status_conciliacao == status_conciliacao.lower())
    if forma_pagamento:
        q = q.filter(Transacao.forma_pagamento == forma_pagamento.lower())
    if data_inicio:
        q = q.filter(Transacao.data_pagamento >= data_inicio)
    if data_fim:
        q = q.filter(Transacao.data_pagamento <= data_fim)

    q = q.order_by(Transacao.data_pagamento.desc())
    total = q.count()
    transacoes = q.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()

    return {
        "items": [_transacao_to_dict(t) for t in transacoes],
        "total": total,
        "page": page,
        "per_page": PER_PAGE,
    }


@router.post("")
def criar_transacao(
    body: TransacaoBody,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.valor <= 0:
        raise HTTPException(status_code=400, detail="O valor deve ser maior que zero")
    try:
        data_pagamento = date.fromisoformat(body.data_pagamento)
    except ValueError:
        raise HTTPException(status_code=400, detail="data_pagamento inválida (use YYYY-MM-DD)")

    transacao = Transacao(
        descricao=body.descricao,
        tipo=body.tipo,
        valor=Decimal(str(body.valor)),
        data_pagamento=data_pagamento,
        conta_id=body.conta_id,
        forma_pagamento=body.forma_pagamento,
        status_conciliacao=StatusConciliacao.pendente,
        usuario_id=current_user.id,
    )
    db.add(transacao)
    db.commit()
    db.refresh(transacao)
    return _transacao_to_dict(transacao)


@router.put("/{transacao_id}")
def editar_transacao(
    transacao_id: int,
    body: TransacaoBody,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.query(Transacao).filter(Transacao.id == transacao_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    if body.valor <= 0:
        raise HTTPException(status_code=400, detail="O valor deve ser maior que zero")
    try:
        data_pagamento = date.fromisoformat(body.data_pagamento)
    except ValueError:
        raise HTTPException(status_code=400, detail="data_pagamento inválida (use YYYY-MM-DD)")

    t.descricao = body.descricao
    t.tipo = body.tipo
    t.valor = Decimal(str(body.valor))
    t.data_pagamento = data_pagamento
    t.conta_id = body.conta_id
    t.forma_pagamento = body.forma_pagamento
    db.commit()
    db.refresh(t)
    return _transacao_to_dict(t)


@router.delete("/{transacao_id}")
def excluir_transacao(
    transacao_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.query(Transacao).filter(Transacao.id == transacao_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    db.delete(t)
    db.commit()
    return {"ok": True}


@router.get("/{transacao_id}/lancamentos-para-vincular")
def lancamentos_para_vincular(
    transacao_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transacao = db.query(Transacao).filter(Transacao.id == transacao_id).first()
    if not transacao:
        raise HTTPException(status_code=404, detail="Transação não encontrada")

    data_min = transacao.data_pagamento - timedelta(days=30)
    data_max = transacao.data_pagamento + timedelta(days=30)
    lancamentos = db.query(Lancamento).filter(
        Lancamento.tipo == transacao.tipo,
        Lancamento.data_competencia >= data_min,
        Lancamento.data_competencia <= data_max,
    ).all()

    return [
        {
            "id": l.id,
            "descricao": l.descricao,
            "tipo": l.tipo,
            "valor_total": float(l.valor_total),
            "valor_pago": float(l.valor_pago),
            "data_competencia": l.data_competencia.isoformat(),
            "status": l.status,
            "categoria_nome": l.categoria.nome if l.categoria else None,
        }
        for l in lancamentos
        if l.status != "realizado"
    ]


@router.get("/{transacao_id}/vinculos")
def vinculos_transacao(
    transacao_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.query(Transacao).filter(Transacao.id == transacao_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transação não encontrada")

    return [
        {
            "id": v.id,
            "lancamento_id": v.lancamento_id,
            "lancamento_descricao": v.lancamento.descricao if v.lancamento else None,
            "lancamento_data": v.lancamento.data_competencia.isoformat() if v.lancamento else None,
            "lancamento_categoria": v.lancamento.categoria.nome if v.lancamento and v.lancamento.categoria else None,
            "valor_vinculado": float(v.valor_vinculado),
        }
        for v in t.vinculos
    ]


@router.delete("/{transacao_id}/vinculos")
def desvincular_todos(
    transacao_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.query(Transacao).filter(Transacao.id == transacao_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transação não encontrada")

    for v in list(t.vinculos):
        db.delete(v)
    t.status_conciliacao = StatusConciliacao.pendente
    db.commit()
    return {"ok": True}


@router.post("/{transacao_id}/vincular")
def vincular_lancamento(
    transacao_id: int,
    body: VincularBody,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.query(Transacao).filter(Transacao.id == transacao_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transação não encontrada")

    lancamento = db.query(Lancamento).filter(Lancamento.id == body.lancamento_id).first()
    if not lancamento:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")

    valor = Decimal(str(body.valor_vinculado))

    if valor <= 0:
        raise HTTPException(status_code=400, detail="O valor vinculado deve ser maior que zero.")

    if valor > t.valor:
        raise HTTPException(
            status_code=400,
            detail=f"Valor vinculado (R$ {valor:.2f}) não pode exceder o valor da transação (R$ {t.valor:.2f}).",
        )

    restante_lancamento = lancamento.valor_total - lancamento.valor_pago
    if valor > restante_lancamento:
        raise HTTPException(
            status_code=400,
            detail=f"Valor vinculado (R$ {valor:.2f}) excede o saldo restante do lançamento (R$ {restante_lancamento:.2f}).",
        )

    vinculo = LancamentoTransacao(
        lancamento_id=body.lancamento_id,
        transacao_id=transacao_id,
        valor_vinculado=valor,
    )
    db.add(vinculo)
    t.status_conciliacao = StatusConciliacao.conciliado
    db.commit()
    return {"ok": True}
