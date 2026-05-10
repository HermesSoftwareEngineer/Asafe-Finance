from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Set

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


def _normalize_periodo(data: date, granularidade: str) -> date:
    if granularidade == "dia":
        return date(data.year, data.month, data.day)
    if granularidade == "semana":
        return data - timedelta(days=data.weekday())
    return date(data.year, data.month, 1)


def _next_period(data: date, granularidade: str) -> date:
    if granularidade == "dia":
        return data + timedelta(days=1)
    if granularidade == "semana":
        return data + timedelta(days=7)
    month = data.month + 1
    year = data.year
    if month > 12:
        month = 1
        year += 1
    return date(year, month, 1)


def _format_periodo(data: date, granularidade: str) -> str:
    if granularidade == "dia":
        return data.strftime("%Y-%m-%d")
    if granularidade == "semana":
        return data.strftime("%Y-%m-%d")
    return data.strftime("%Y-%m")


def _filter_categorias(cats: List[Categoria], categoria_ids: Optional[List[int]]) -> List[Categoria]:
    if not categoria_ids:
        return cats
    selected: Set[int] = set(categoria_ids)
    included_by_id: Dict[int, Categoria] = {}
    for cat in cats:
        if cat.id in selected or (cat.categoria_pai_id and cat.categoria_pai_id in selected):
            included_by_id[cat.id] = cat
    for cat in list(included_by_id.values()):
        if cat.categoria_pai_id and cat.categoria_pai_id not in included_by_id:
            parent = next((c for c in cats if c.id == cat.categoria_pai_id), None)
            if parent:
                included_by_id[parent.id] = parent
    return list(included_by_id.values())


def por_categoria(
    db: Session,
    data_inicio: date,
    data_fim: date,
    categoria_ids: Optional[List[int]] = None,
    granularidade: str = "mes",
):
    cats = db.query(Categoria).filter(Categoria.ativo == True).all()
    cats = _filter_categorias(cats, categoria_ids)
    cats_by_id = {c.id: c for c in cats}
    if not cats:
        return {"categorias": [], "pie": {"entrada": {"total": 0.0, "items": []}, "saida": {"total": 0.0, "items": []}}, "series": {"granularidade": granularidade, "items": []}}

    root_categories = [cat for cat in cats if cat.categoria_pai_id is None or cat.categoria_pai_id not in cats_by_id]
    children_by_parent: Dict[int, List[Categoria]] = {}
    for cat in cats:
        if cat.categoria_pai_id and cat.categoria_pai_id in cats_by_id:
            children_by_parent.setdefault(cat.categoria_pai_id, []).append(cat)

    lancamentos = db.query(Lancamento).filter(
        Lancamento.data >= data_inicio,
        Lancamento.data <= data_fim,
        Lancamento.categoria_id.in_(list(cats_by_id.keys())),
    ).all()

    totals_by_category: Dict[int, Decimal] = {cat.id: Decimal("0") for cat in cats}
    series_map: Dict[str, Dict[str, Decimal]] = {}
    for lancamento in lancamentos:
        if lancamento.categoria_id not in totals_by_category:
            continue
        totals_by_category[lancamento.categoria_id] += lancamento.valor_total
        periodo_data = _normalize_periodo(lancamento.data, granularidade)
        periodo_key = _format_periodo(periodo_data, granularidade)
        if periodo_key not in series_map:
            series_map[periodo_key] = {"entrada": Decimal("0"), "saida": Decimal("0")}
        series_map[periodo_key][lancamento.tipo] += lancamento.valor_total

    pie_by_tipo = {"entrada": {"total": Decimal("0"), "items": []}, "saida": {"total": Decimal("0"), "items": []}}
    categorias_result = []
    for root in sorted(root_categories, key=lambda c: c.nome):
        children = sorted(children_by_parent.get(root.id, []), key=lambda c: c.nome)
        total_root = totals_by_category[root.id] + sum(totals_by_category[c.id] for c in children)
        subcategorias = [
            {"categoria_id": child.id, "categoria_nome": child.nome, "total": float(totals_by_category[child.id])}
            for child in children
        ]
        categorias_result.append({
            "categoria_id": root.id,
            "categoria_nome": root.nome,
            "categoria_tipo": root.tipo,
            "total": float(total_root),
            "subcategorias": subcategorias,
        })
        pie_by_tipo[root.tipo]["total"] += total_root

    for root in sorted(root_categories, key=lambda c: c.nome):
        total_root = Decimal("0")
        children = sorted(children_by_parent.get(root.id, []), key=lambda c: c.nome)
        total_root = totals_by_category[root.id] + sum(totals_by_category[c.id] for c in children)
        pato = pie_by_tipo[root.tipo]
        percentage = float((total_root / pato["total"] * 100) if pato["total"] else Decimal("0"))
        pato["items"].append({
            "categoria_id": root.id,
            "categoria_nome": root.nome,
            "total": float(total_root),
            "percentual": percentage,
        })
        for child in children:
            percentual_child = float((totals_by_category[child.id] / pato["total"] * 100) if pato["total"] else Decimal("0"))
            pato["items"].append({
                "categoria_id": child.id,
                "categoria_nome": child.nome,
                "categoria_pai_id": root.id,
                "total": float(totals_by_category[child.id]),
                "percentual": percentual_child,
            })

    series_items = []
    current_period = _normalize_periodo(data_inicio, granularidade)
    end_period = _normalize_periodo(data_fim, granularidade)
    while current_period <= end_period:
        key = _format_periodo(current_period, granularidade)
        values = series_map.get(key, {"entrada": Decimal("0"), "saida": Decimal("0")})
        series_items.append({
            "periodo": key,
            "entrada": float(values["entrada"]),
            "saida": float(values["saida"]),
            "saldo": float(values["entrada"] - values["saida"]),
        })
        current_period = _next_period(current_period, granularidade)

    return {
        "categorias": categorias_result,
        "pie": {
            "entrada": {
                "total": float(pie_by_tipo["entrada"]["total"]),
                "items": pie_by_tipo["entrada"]["items"],
            },
            "saida": {
                "total": float(pie_by_tipo["saida"]["total"]),
                "items": pie_by_tipo["saida"]["items"],
            },
        },
        "series": {"granularidade": granularidade, "items": series_items},
    }


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


def saldo_contas(db: Session, data_alvo: date, conta_id: Optional[int] = None):
    q_contas = db.query(Conta).filter(Conta.ativo == True)
    if conta_id:
        q_contas = q_contas.filter(Conta.id == conta_id)
    contas = q_contas.all()

    rows = []
    for conta in contas:
        lancamentos = (
            db.query(Lancamento)
            .filter(
                Lancamento.conta_id == conta.id,
                Lancamento.status == "pago",
                Lancamento.data <= data_alvo
            )
            .all()
        )
        
        saldo = conta.saldo_inicial
        entradas = sum(l.valor_total for l in lancamentos if l.tipo == "entrada")
        saidas = sum(l.valor_total for l in lancamentos if l.tipo == "saida")
        saldo += entradas - saidas
        
        rows.append({
            "conta_id": conta.id,
            "conta_nome": conta.nome,
            "conta_tipo": conta.tipo,
            "saldo_inicial": conta.saldo_inicial,
            "entradas": entradas,
            "saidas": saidas,
            "saldo": saldo,
        })
        
    return rows
