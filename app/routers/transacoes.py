from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    Conta, Lancamento, LancamentoTransacao, StatusConciliacao, Transacao, Usuario,
)
from app.templates_config import templates


router = APIRouter(prefix="/transacoes")


@router.get("", response_class=HTMLResponse)
async def listar_transacoes(
    request: Request,
    page: int = Query(1, ge=1),
    conta_id: Optional[int] = None,
    status_conciliacao: Optional[str] = None,
    forma_pagamento: Optional[str] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    per_page = 20
    q = db.query(Transacao)
    if conta_id:
        q = q.filter(Transacao.conta_id == conta_id)
    if status_conciliacao:
        q = q.filter(Transacao.status_conciliacao == status_conciliacao)
    if forma_pagamento:
        q = q.filter(Transacao.forma_pagamento == forma_pagamento)
    if data_inicio:
        q = q.filter(Transacao.data_pagamento >= data_inicio)
    if data_fim:
        q = q.filter(Transacao.data_pagamento <= data_fim)

    q = q.order_by(Transacao.data_pagamento.desc())
    total = q.count()
    transacoes = q.offset((page - 1) * per_page).limit(per_page).all()
    contas = db.query(Conta).filter(Conta.ativo == True).all()

    return templates.TemplateResponse("transacoes/lista.html", {
        "request": request, "current_user": current_user,
        "transacoes": transacoes, "contas": contas,
        "page": page, "total": total, "per_page": per_page,
        "filtros": {
            "conta_id": conta_id, "status_conciliacao": status_conciliacao,
            "forma_pagamento": forma_pagamento, "data_inicio": data_inicio, "data_fim": data_fim,
        },
    })


@router.get("/nova", response_class=HTMLResponse)
async def form_nova(
    request: Request,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contas = db.query(Conta).filter(Conta.ativo == True).all()
    return templates.TemplateResponse("transacoes/form.html", {
        "request": request, "current_user": current_user,
        "transacao": None, "contas": contas, "error": None,
    })


@router.post("/nova", response_class=HTMLResponse)
async def criar_transacao(
    request: Request,
    descricao: str = Form(...),
    tipo: str = Form(...),
    valor: Decimal = Form(...),
    data_pagamento: date = Form(...),
    conta_id: int = Form(...),
    forma_pagamento: str = Form(...),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contas = db.query(Conta).filter(Conta.ativo == True).all()
    ctx = {"request": request, "current_user": current_user, "transacao": None, "contas": contas, "error": None}
    if valor <= 0:
        ctx["error"] = "O valor deve ser maior que zero."
        return templates.TemplateResponse("transacoes/form.html", ctx)

    transacao = Transacao(
        descricao=descricao, tipo=tipo, valor=valor, data_pagamento=data_pagamento,
        conta_id=conta_id, forma_pagamento=forma_pagamento,
        status_conciliacao=StatusConciliacao.pendente, usuario_id=current_user.id,
    )
    db.add(transacao)
    db.commit()
    hx = request.headers.get("HX-Request")
    if hx:
        return HTMLResponse('<div id="modal-container"></div><script>window.location.reload();</script>')
    return RedirectResponse("/transacoes", status_code=302)


@router.get("/{transacao_id}/editar", response_class=HTMLResponse)
async def form_editar(
    transacao_id: int,
    request: Request,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transacao = db.query(Transacao).filter(Transacao.id == transacao_id).first()
    if not transacao:
        raise HTTPException(404)
    contas = db.query(Conta).filter(Conta.ativo == True).all()
    return templates.TemplateResponse("transacoes/form.html", {
        "request": request, "current_user": current_user,
        "transacao": transacao, "contas": contas, "error": None,
    })


@router.post("/{transacao_id}/editar", response_class=HTMLResponse)
async def editar_transacao(
    transacao_id: int,
    request: Request,
    descricao: str = Form(...),
    tipo: str = Form(...),
    valor: Decimal = Form(...),
    data_pagamento: date = Form(...),
    conta_id: int = Form(...),
    forma_pagamento: str = Form(...),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.query(Transacao).filter(Transacao.id == transacao_id).first()
    if not t:
        raise HTTPException(404)
    t.descricao = descricao
    t.tipo = tipo
    t.valor = valor
    t.data_pagamento = data_pagamento
    t.conta_id = conta_id
    t.forma_pagamento = forma_pagamento
    db.commit()
    hx = request.headers.get("HX-Request")
    if hx:
        return HTMLResponse('<div id="modal-container"></div><script>window.location.reload();</script>')
    return RedirectResponse("/transacoes", status_code=302)


@router.post("/{transacao_id}/excluir")
async def excluir_transacao(
    transacao_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.query(Transacao).filter(Transacao.id == transacao_id).first()
    if t:
        db.delete(t)
        db.commit()
    return RedirectResponse("/transacoes", status_code=302)


@router.get("/{transacao_id}/vincular", response_class=HTMLResponse)
async def buscar_lancamentos_para_vincular(
    transacao_id: int,
    request: Request,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transacao = db.query(Transacao).filter(Transacao.id == transacao_id).first()
    if not transacao:
        raise HTTPException(404)
    from datetime import timedelta
    data_min = transacao.data_pagamento - timedelta(days=30)
    data_max = transacao.data_pagamento + timedelta(days=30)
    lancamentos = db.query(Lancamento).filter(
        Lancamento.tipo == transacao.tipo,
        Lancamento.data_competencia >= data_min,
        Lancamento.data_competencia <= data_max,
    ).all()
    return templates.TemplateResponse("transacoes/vincular.html", {
        "request": request, "current_user": current_user,
        "transacao": transacao, "lancamentos": lancamentos,
    })


@router.post("/{transacao_id}/vincular")
async def vincular_lancamento(
    transacao_id: int,
    lancamento_id: int = Form(...),
    valor_vinculado: Decimal = Form(...),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vinculo = LancamentoTransacao(
        lancamento_id=lancamento_id,
        transacao_id=transacao_id,
        valor_vinculado=valor_vinculado,
    )
    db.add(vinculo)
    t = db.query(Transacao).get(transacao_id)
    if t:
        t.status_conciliacao = StatusConciliacao.conciliado
    db.commit()
