from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Conta, Lancamento, StatusConciliacao, Transacao, Usuario

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    fim_mes = (inicio_mes.replace(month=inicio_mes.month % 12 + 1, day=1) if inicio_mes.month < 12
               else inicio_mes.replace(year=inicio_mes.year + 1, month=1, day=1)) - timedelta(days=1)

    # Saldo por conta
    contas = db.query(Conta).filter(Conta.ativo == True).all()
    saldos_conta = []
    saldo_total = Decimal("0.00")
    for conta in contas:
        entradas = db.query(func.sum(Transacao.valor)).filter(
            Transacao.conta_id == conta.id, Transacao.tipo == "entrada"
        ).scalar() or Decimal("0.00")
        saidas = db.query(func.sum(Transacao.valor)).filter(
            Transacao.conta_id == conta.id, Transacao.tipo == "saida"
        ).scalar() or Decimal("0.00")
        saldo = conta.saldo_inicial + entradas - saidas
        saldo_total += saldo
        saldos_conta.append({"conta": conta, "saldo": saldo})

    # Entradas e saídas do mês (por transações)
    entradas_mes = db.query(func.sum(Transacao.valor)).filter(
        Transacao.tipo == "entrada",
        Transacao.data_pagamento >= inicio_mes,
        Transacao.data_pagamento <= fim_mes,
    ).scalar() or Decimal("0.00")

    saidas_mes = db.query(func.sum(Transacao.valor)).filter(
        Transacao.tipo == "saida",
        Transacao.data_pagamento >= inicio_mes,
        Transacao.data_pagamento <= fim_mes,
    ).scalar() or Decimal("0.00")

    # Lançamentos vencidos não realizados
    lancamentos_vencidos = db.query(Lancamento).filter(
        Lancamento.data_competencia < hoje,
    ).all()
    lancamentos_vencidos = [l for l in lancamentos_vencidos if l.status != "realizado"]

    # Transações pendentes de conciliação
    pendentes_conciliacao = db.query(func.count(Transacao.id)).filter(
        Transacao.status_conciliacao == StatusConciliacao.pendente
    ).scalar() or 0

    # Dados para gráfico de linha (entradas e saídas por dia no mês)
    dias = []
    d = inicio_mes
    while d <= min(fim_mes, hoje):
        dias.append(d)
        d += timedelta(days=1)

    chart_labels = [d.strftime("%d/%m") for d in dias]
    chart_entradas = []
    chart_saidas = []
    for d in dias:
        e = db.query(func.sum(Transacao.valor)).filter(
            Transacao.tipo == "entrada", Transacao.data_pagamento == d
        ).scalar() or 0
        s = db.query(func.sum(Transacao.valor)).filter(
            Transacao.tipo == "saida", Transacao.data_pagamento == d
        ).scalar() or 0
        chart_entradas.append(float(e))
        chart_saidas.append(float(s))

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "current_user": current_user,
        "saldo_total": saldo_total,
        "saldos_conta": saldos_conta,
        "entradas_mes": entradas_mes,
        "saidas_mes": saidas_mes,
        "lancamentos_vencidos": lancamentos_vencidos,
        "pendentes_conciliacao": pendentes_conciliacao,
        "chart_labels": chart_labels,
        "chart_entradas": chart_entradas,
        "chart_saidas": chart_saidas,
        "hoje": hoje,
    })
