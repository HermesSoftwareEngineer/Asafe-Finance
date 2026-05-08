from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Categoria, CentroCusto, Conta, Lancamento


def fluxo_de_caixa(db: Session, data_inicio: date, data_fim: date, conta_id: Optional[int] = None):
    q = db.query(Lancamento).filter(
        Lancamento.status == "pago",
        Lancamento.data >= data_inicio,
        Lancamento.data <= data_fim,
    )
    if conta_id:
        q = q.filter(Lancamento.conta_id == conta_id)
    lancamentos = q.order_by(Lancamento.data).all()

    resumo_por_periodo = {}
    for l in lancamentos:
        key = l.data.strftime("%Y-%m")
        if key not in resumo_por_periodo:
            resumo_por_periodo[key] = {"entradas": Decimal("0"), "saidas": Decimal("0")}
        if l.tipo == "entrada":
            resumo_por_periodo[key]["entradas"] += l.valor_total
        else:
            resumo_por_periodo[key]["saidas"] += l.valor_total

    rows = []
    saldo_acumulado = Decimal("0")
    for periodo, vals in sorted(resumo_por_periodo.items()):
        saldo = vals["entradas"] - vals["saidas"]
        saldo_acumulado += saldo
        rows.append({
            "periodo": periodo,
            "entradas": vals["entradas"],
            "saidas": vals["saidas"],
            "saldo": saldo,
            "saldo_acumulado": saldo_acumulado,
        })
    return rows


def por_categoria(db: Session, data_inicio: date, data_fim: date):
    cats = db.query(Categoria).filter(Categoria.ativo == True).all()
    resultado = []
    for cat in cats:
        if cat.categoria_pai_id is not None:
            continue
        filhos = [c for c in cats if c.categoria_pai_id == cat.id]
        total_cat = Decimal("0")
        sub_rows = []
        targets = filhos if filhos else [cat]
        for target in targets:
            lancamentos = db.query(Lancamento).filter(
                Lancamento.categoria_id == target.id,
                Lancamento.data >= data_inicio,
                Lancamento.data <= data_fim,
            ).all()
            total_sub = sum(l.valor_total for l in lancamentos)
            total_cat += total_sub
            if filhos:
                sub_rows.append({"categoria": target, "total": total_sub})
        resultado.append({"categoria": cat, "total": total_cat, "subcategorias": sub_rows})
    return resultado


def por_centro_custo(db: Session, data_inicio: date, data_fim: date):
    centros = db.query(CentroCusto).filter(CentroCusto.ativo == True).all()
    rows = []
    for centro in centros:
        lancamentos = db.query(Lancamento).filter(
            Lancamento.centro_custo_id == centro.id,
            Lancamento.data >= data_inicio,
            Lancamento.data <= data_fim,
        ).all()
        entradas = sum(l.valor_total for l in lancamentos if l.tipo == "entrada")
        saidas = sum(l.valor_total for l in lancamentos if l.tipo == "saida")
        rows.append({"centro": centro, "entradas": entradas, "saidas": saidas, "saldo": entradas - saidas})
    return rows


def previsto_vs_realizado(db: Session, data_inicio: date, data_fim: date):
    cats = db.query(Categoria).filter(Categoria.ativo == True).all()
    rows = []
    for cat in cats:
        lancamentos = db.query(Lancamento).filter(
            Lancamento.categoria_id == cat.id,
            Lancamento.data >= data_inicio,
            Lancamento.data <= data_fim,
        ).all()
        if not lancamentos:
            continue
        previsto = sum(l.valor_total for l in lancamentos if l.status == "a pagar")
        realizado = sum(l.valor_total for l in lancamentos if l.status == "pago")
        total = previsto + realizado
        diferenca = realizado - previsto
        percentual = (realizado / total * 100) if total else Decimal("0")
        rows.append({
            "categoria": cat,
            "previsto": previsto,
            "realizado": realizado,
            "diferenca": diferenca,
            "percentual": percentual,
        })
    return rows


def extrato_conta(db: Session, conta_id: int, data_inicio: date, data_fim: date):
    conta = db.query(Conta).filter(Conta.id == conta_id).first()
    if not conta:
        return None, []
    lancamentos = (
        db.query(Lancamento)
        .filter(
            Lancamento.conta_id == conta_id,
            Lancamento.status == "pago",
            Lancamento.data >= data_inicio,
            Lancamento.data <= data_fim,
        )
        .order_by(Lancamento.data)
        .all()
    )
    saldo_corrente = conta.saldo_inicial
    rows = []
    for l in lancamentos:
        if l.tipo == "entrada":
            saldo_corrente += l.valor_total
        else:
            saldo_corrente -= l.valor_total
        rows.append({"lancamento": l, "saldo_corrente": saldo_corrente})
    return conta, rows
