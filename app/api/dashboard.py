from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Conta, Lancamento, OfxTransaction, StatusConciliacao, StatusOfxTransaction, Usuario
from app.api.deps import get_current_user


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    fim_mes = (
        inicio_mes.replace(month=inicio_mes.month % 12 + 1, day=1)
        if inicio_mes.month < 12
        else inicio_mes.replace(year=inicio_mes.year + 1, month=1, day=1)
    ) - timedelta(days=1)

    # Saldo por conta (somente lançamentos pagos)
    contas = db.query(Conta).filter(Conta.ativo == True).all()
    saldos_conta = []
    saldo_total = Decimal("0.00")
    for conta in contas:
        entradas = db.query(func.sum(Lancamento.valor_total)).filter(
            Lancamento.conta_id == conta.id,
            Lancamento.tipo == "entrada",
            Lancamento.status == "pago",
        ).scalar() or Decimal("0.00")
        saidas = db.query(func.sum(Lancamento.valor_total)).filter(
            Lancamento.conta_id == conta.id,
            Lancamento.tipo == "saida",
            Lancamento.status == "pago",
        ).scalar() or Decimal("0.00")
        saldo = conta.saldo_inicial + entradas - saidas
        saldo_total += saldo
        saldos_conta.append({
            "id": conta.id,
            "nome": conta.nome,
            "tipo": conta.tipo,
            "saldo": float(saldo),
        })

    # Entradas e saídas do mês (lançamentos pagos no mês)
    entradas_mes = db.query(func.sum(Lancamento.valor_total)).filter(
        Lancamento.tipo == "entrada",
        Lancamento.status == "pago",
        Lancamento.data >= inicio_mes,
        Lancamento.data <= fim_mes,
    ).scalar() or Decimal("0.00")

    saidas_mes = db.query(func.sum(Lancamento.valor_total)).filter(
        Lancamento.tipo == "saida",
        Lancamento.status == "pago",
        Lancamento.data >= inicio_mes,
        Lancamento.data <= fim_mes,
    ).scalar() or Decimal("0.00")

    # Lançamentos a pagar com data vencida
    lancamentos_vencidos = db.query(func.count(Lancamento.id)).filter(
        Lancamento.status == "a pagar",
        Lancamento.data < hoje,
    ).scalar() or 0

    # OFX pendentes de conciliação
    ofx_pendentes = db.query(func.count(OfxTransaction.id)).filter(
        OfxTransaction.status == StatusOfxTransaction.pendente,
    ).scalar() or 0

    # Lançamentos pagos não conciliados
    lancamentos_nao_conciliados = db.query(func.count(Lancamento.id)).filter(
        Lancamento.status == "pago",
        Lancamento.status_conciliacao == StatusConciliacao.pendente,
    ).scalar() or 0

    # Gráfico: lançamentos pagos por dia no mês
    dias = []
    d = inicio_mes
    while d <= min(fim_mes, hoje):
        dias.append(d)
        d += timedelta(days=1)

    chart_labels = [d.strftime("%d/%m") for d in dias]
    chart_entradas = []
    chart_saidas = []
    for d in dias:
        e = db.query(func.sum(Lancamento.valor_total)).filter(
            Lancamento.tipo == "entrada",
            Lancamento.status == "pago",
            Lancamento.data == d,
        ).scalar() or 0
        s = db.query(func.sum(Lancamento.valor_total)).filter(
            Lancamento.tipo == "saida",
            Lancamento.status == "pago",
            Lancamento.data == d,
        ).scalar() or 0
        chart_entradas.append(float(e))
        chart_saidas.append(float(s))

    return {
        "saldo_total": float(saldo_total),
        "entradas_mes": float(entradas_mes),
        "saidas_mes": float(saidas_mes),
        "lancamentos_vencidos": lancamentos_vencidos,
        "ofx_pendentes": ofx_pendentes,
        "lancamentos_nao_conciliados": lancamentos_nao_conciliados,
        "saldos_conta": saldos_conta,
        "chart_labels": chart_labels,
        "chart_entradas": chart_entradas,
        "chart_saidas": chart_saidas,
    }
