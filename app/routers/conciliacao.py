from datetime import timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    Conta, Lancamento, LancamentoTransacao, OfxImport,
    StatusConciliacao, Transacao, Usuario,
)
from app.services.ofx_service import importar_ofx

router = APIRouter(prefix="/conciliacao")
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
async def conciliacao_page(
    request: Request,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contas = db.query(Conta).filter(Conta.ativo == True).all()
    pendentes = (
        db.query(Transacao)
        .filter(Transacao.status_conciliacao == StatusConciliacao.pendente)
        .order_by(Transacao.data_pagamento.desc())
        .all()
    )
    historico = db.query(OfxImport).order_by(OfxImport.importado_em.desc()).limit(20).all()

    # For each pending transaction, find compatible lancamentos
    sugestoes = {}
    for t in pendentes:
        data_min = t.data_pagamento - timedelta(days=15)
        data_max = t.data_pagamento + timedelta(days=15)
        candidatos = db.query(Lancamento).filter(
            Lancamento.tipo == t.tipo,
            Lancamento.data_competencia >= data_min,
            Lancamento.data_competencia <= data_max,
        ).all()
        sugestoes[t.id] = [l for l in candidatos if l.status != "realizado"]

    return templates.TemplateResponse("conciliacao/index.html", {
        "request": request, "current_user": current_user,
        "contas": contas, "pendentes": pendentes,
        "sugestoes": sugestoes, "historico": historico,
    })


@router.post("/upload")
async def upload_ofx(
    request: Request,
    conta_id: int = Form(...),
    arquivo: UploadFile = File(...),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conta = db.query(Conta).filter(Conta.id == conta_id).first()
    if not conta:
        raise HTTPException(404, "Conta não encontrada.")

    conteudo = await arquivo.read()
    try:
        resultado = importar_ofx(conteudo, arquivo.filename, conta, current_user, db)
        msg = f"Importação concluída: {resultado['importadas']} novas, {resultado['duplicatas']} duplicatas ignoradas."
    except ValueError as e:
        msg = str(e)

    contas = db.query(Conta).filter(Conta.ativo == True).all()
    pendentes = (
        db.query(Transacao)
        .filter(Transacao.status_conciliacao == StatusConciliacao.pendente)
        .order_by(Transacao.data_pagamento.desc())
        .all()
    )
    historico = db.query(OfxImport).order_by(OfxImport.importado_em.desc()).limit(20).all()
    sugestoes = {}
    for t in pendentes:
        data_min = t.data_pagamento - timedelta(days=15)
        data_max = t.data_pagamento + timedelta(days=15)
        candidatos = db.query(Lancamento).filter(
            Lancamento.tipo == t.tipo,
            Lancamento.data_competencia >= data_min,
            Lancamento.data_competencia <= data_max,
        ).all()
        sugestoes[t.id] = [l for l in candidatos if l.status != "realizado"]

    return templates.TemplateResponse("conciliacao/index.html", {
        "request": request, "current_user": current_user,
        "contas": contas, "pendentes": pendentes,
        "sugestoes": sugestoes, "historico": historico,
        "mensagem": msg,
    })


@router.post("/vincular/{transacao_id}")
async def vincular_transacao(
    transacao_id: int,
    lancamento_id: int = Form(...),
    valor_vinculado: Decimal = Form(...),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.query(Transacao).filter(Transacao.id == transacao_id).first()
    if not t:
        raise HTTPException(404)
    vinculo = LancamentoTransacao(
        lancamento_id=lancamento_id, transacao_id=transacao_id, valor_vinculado=valor_vinculado
    )
    db.add(vinculo)
    t.status_conciliacao = StatusConciliacao.conciliado
    db.commit()
    return RedirectResponse("/conciliacao", status_code=302)


@router.post("/ignorar/{transacao_id}")
async def ignorar_transacao(
    transacao_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.query(Transacao).filter(Transacao.id == transacao_id).first()
    if t:
        t.status_conciliacao = StatusConciliacao.ignorado
        db.commit()
    return RedirectResponse("/conciliacao", status_code=302)


@router.post("/criar-lancamento/{transacao_id}")
async def criar_lancamento_da_transacao(
    transacao_id: int,
    descricao: str = Form(...),
    categoria_id: Optional[int] = Form(None),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    t = db.query(Transacao).filter(Transacao.id == transacao_id).first()
    if not t:
        raise HTTPException(404)

    lancamento = Lancamento(
        descricao=descricao, tipo=t.tipo, valor_total=t.valor,
        data_competencia=t.data_pagamento, categoria_id=categoria_id or None,
        usuario_id=current_user.id,
    )
    db.add(lancamento)
    db.flush()

    vinculo = LancamentoTransacao(
        lancamento_id=lancamento.id, transacao_id=transacao_id, valor_vinculado=t.valor
    )
    db.add(vinculo)
    t.status_conciliacao = StatusConciliacao.conciliado
    db.commit()
    return RedirectResponse("/conciliacao", status_code=302)
