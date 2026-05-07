from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Lancamento, LancamentoTransacao, StatusConciliacao, Transacao, Usuario
from app.api.deps import get_current_user


router = APIRouter(prefix="/api/lancamentos", tags=["lancamentos"])

PER_PAGE = 20


class LancamentoBody(BaseModel):
    descricao: str
    tipo: str
    valor_total: float
    data_competencia: str
    categoria_id: Optional[int] = None
    centro_custo_id: Optional[int] = None
    observacao: Optional[str] = None


def _lancamento_to_dict(l: Lancamento) -> dict:
    return {
        "id": l.id,
        "descricao": l.descricao,
        "tipo": l.tipo,
        "valor_total": float(l.valor_total),
        "valor_pago": float(l.valor_pago),
        "data_competencia": l.data_competencia.isoformat(),
        "status": l.status,
        "categoria_id": l.categoria_id,
        "categoria_nome": l.categoria.nome if l.categoria else None,
        "centro_custo_id": l.centro_custo_id,
        "centro_custo_nome": l.centro_custo.nome if l.centro_custo else None,
        "observacao": l.observacao,
    }


@router.get("")
def listar_lancamentos(
    page: int = Query(1, ge=1),
    tipo: Optional[str] = None,
    status: Optional[str] = None,
    categoria_id: Optional[int] = None,
    centro_custo_id: Optional[int] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Lancamento)
    if tipo:
        q = q.filter(Lancamento.tipo == tipo)
    if categoria_id:
        q = q.filter(Lancamento.categoria_id == categoria_id)
    if centro_custo_id:
        q = q.filter(Lancamento.centro_custo_id == centro_custo_id)
    if data_inicio:
        q = q.filter(Lancamento.data_competencia >= data_inicio)
    if data_fim:
        q = q.filter(Lancamento.data_competencia <= data_fim)

    q = q.order_by(Lancamento.data_competencia.desc())
    total = q.count()
    lancamentos = q.offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()

    # Filter by status (computed property — filter in Python)
    if status:
        lancamentos = [l for l in lancamentos if l.status == status]

    return {
        "items": [_lancamento_to_dict(l) for l in lancamentos],
        "total": total,
        "page": page,
        "per_page": PER_PAGE,
    }


@router.post("")
def criar_lancamento(
    body: LancamentoBody,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.valor_total <= 0:
        raise HTTPException(status_code=400, detail="O valor deve ser maior que zero")
    try:
        data_competencia = date.fromisoformat(body.data_competencia)
    except ValueError:
        raise HTTPException(status_code=400, detail="data_competencia inválida (use YYYY-MM-DD)")

    lancamento = Lancamento(
        descricao=body.descricao,
        tipo=body.tipo,
        valor_total=Decimal(str(body.valor_total)),
        data_competencia=data_competencia,
        categoria_id=body.categoria_id or None,
        centro_custo_id=body.centro_custo_id or None,
        observacao=body.observacao,
        usuario_id=current_user.id,
    )
    db.add(lancamento)
    db.commit()
    db.refresh(lancamento)
    return _lancamento_to_dict(lancamento)


@router.put("/{lancamento_id}")
def editar_lancamento(
    lancamento_id: int,
    body: LancamentoBody,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lancamento = db.query(Lancamento).filter(Lancamento.id == lancamento_id).first()
    if not lancamento:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    if body.valor_total <= 0:
        raise HTTPException(status_code=400, detail="O valor deve ser maior que zero")
    try:
        data_competencia = date.fromisoformat(body.data_competencia)
    except ValueError:
        raise HTTPException(status_code=400, detail="data_competencia inválida (use YYYY-MM-DD)")

    lancamento.descricao = body.descricao
    lancamento.tipo = body.tipo
    lancamento.valor_total = Decimal(str(body.valor_total))
    lancamento.data_competencia = data_competencia
    lancamento.categoria_id = body.categoria_id or None
    lancamento.centro_custo_id = body.centro_custo_id or None
    lancamento.observacao = body.observacao
    db.commit()
    db.refresh(lancamento)
    return _lancamento_to_dict(lancamento)


@router.delete("/{lancamento_id}")
def excluir_lancamento(
    lancamento_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lancamento = db.query(Lancamento).filter(Lancamento.id == lancamento_id).first()
    if not lancamento:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    db.delete(lancamento)
    db.commit()
    return {"ok": True}


@router.get("/{lancamento_id}/vinculos")
def vinculos_lancamento(
    lancamento_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lancamento = db.query(Lancamento).filter(Lancamento.id == lancamento_id).first()
    if not lancamento:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")

    result = []
    for v in lancamento.vinculos:
        t = v.transacao
        result.append({
            "id": v.id,
            "transacao_id": v.transacao_id,
            "transacao_descricao": t.descricao if t else None,
            "transacao_data": t.data_pagamento.isoformat() if t else None,
            "transacao_conta": t.conta.nome if t and t.conta else None,
            "valor_vinculado": float(v.valor_vinculado),
        })
    return result


@router.delete("/{lancamento_id}/vinculos/{vinculo_id}")
def desvincular_transacao(
    lancamento_id: int,
    vinculo_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vinculo = db.query(LancamentoTransacao).filter(
        LancamentoTransacao.id == vinculo_id,
        LancamentoTransacao.lancamento_id == lancamento_id,
    ).first()
    if not vinculo:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado")

    transacao = vinculo.transacao
    db.delete(vinculo)
    if transacao:
        transacao.status_conciliacao = StatusConciliacao.pendente
    db.commit()
    return {"ok": True}


@router.get("/{lancamento_id}/transacoes-para-vincular")
def transacoes_para_vincular(
    lancamento_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lancamento = db.query(Lancamento).filter(Lancamento.id == lancamento_id).first()
    if not lancamento:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")

    ja_vinculadas = {v.transacao_id for v in lancamento.vinculos}
    transacoes = db.query(Transacao).filter(
        Transacao.tipo == lancamento.tipo,
        Transacao.status_conciliacao == "pendente",
    ).order_by(Transacao.data_pagamento.desc()).all()

    return [
        {
            "id": t.id,
            "descricao": t.descricao,
            "tipo": t.tipo,
            "valor": float(t.valor),
            "data_pagamento": t.data_pagamento.isoformat(),
            "conta_nome": t.conta.nome if t.conta else None,
            "forma_pagamento": t.forma_pagamento,
        }
        for t in transacoes
        if t.id not in ja_vinculadas
    ]
