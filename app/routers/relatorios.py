from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Conta, Usuario
from app.services import relatorio_service, export_service
from app.templates_config import templates


router = APIRouter(prefix="/relatorios")

_HOJE = date.today
_MES_INICIO = lambda: date.today().replace(day=1)


def _parse_datas(data_inicio, data_fim):
    hoje = date.today()
    di = data_inicio or hoje.replace(day=1)
    df = data_fim or hoje
    return di, df


@router.get("", response_class=HTMLResponse)
async def relatorios_home(request: Request, current_user: Usuario = Depends(get_current_user)):
    return templates.TemplateResponse("relatorios/index.html", {"request": request, "current_user": current_user})


@router.get("/fluxo-caixa", response_class=HTMLResponse)
async def fluxo_caixa(
    request: Request,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    conta_id: Optional[int] = None,
    formato: Optional[str] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    di, df = _parse_datas(data_inicio, data_fim)
    dados = relatorio_service.fluxo_de_caixa(db, di, df, conta_id)
    contas = db.query(Conta).filter(Conta.ativo == True).all()

    if formato == "pdf":
        headers = ["Período", "Entradas (R$)", "Saídas (R$)", "Saldo (R$)", "Saldo Acumulado (R$)"]
        rows = [[r["periodo"], f"{r['entradas']:.2f}", f"{r['saidas']:.2f}", f"{r['saldo']:.2f}", f"{r['saldo_acumulado']:.2f}"] for r in dados]
        pdf = export_service.export_pdf("Fluxo de Caixa", headers, rows)
        return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=fluxo_caixa.pdf"})
    if formato == "excel":
        headers = ["Período", "Entradas (R$)", "Saídas (R$)", "Saldo (R$)", "Saldo Acumulado (R$)"]
        rows = [[r["periodo"], float(r["entradas"]), float(r["saidas"]), float(r["saldo"]), float(r["saldo_acumulado"])] for r in dados]
        xls = export_service.export_excel("Fluxo de Caixa", headers, rows)
        return Response(xls, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=fluxo_caixa.xlsx"})

    return templates.TemplateResponse("relatorios/fluxo_caixa.html", {
        "request": request, "current_user": current_user,
        "dados": dados, "contas": contas,
        "data_inicio": di, "data_fim": df, "conta_id": conta_id,
    })


@router.get("/por-categoria", response_class=HTMLResponse)
async def por_categoria(
    request: Request,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    formato: Optional[str] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    di, df = _parse_datas(data_inicio, data_fim)
    dados = relatorio_service.por_categoria(db, di, df)

    if formato == "pdf":
        headers = ["Categoria", "Subcategoria", "Total (R$)"]
        rows = []
        for d in dados:
            if d["subcategorias"]:
                for s in d["subcategorias"]:
                    rows.append([d["categoria"].nome, s["categoria"].nome, f"{s['total']:.2f}"])
            else:
                rows.append([d["categoria"].nome, "-", f"{d['total']:.2f}"])
        pdf = export_service.export_pdf("Relatório por Categoria", headers, rows)
        return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=por_categoria.pdf"})
    if formato == "excel":
        headers = ["Categoria", "Subcategoria", "Total (R$)"]
        rows = []
        for d in dados:
            if d["subcategorias"]:
                for s in d["subcategorias"]:
                    rows.append([d["categoria"].nome, s["categoria"].nome, float(s["total"])])
            else:
                rows.append([d["categoria"].nome, "-", float(d["total"])])
        xls = export_service.export_excel("Por Categoria", headers, rows)
        return Response(xls, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=por_categoria.xlsx"})

    return templates.TemplateResponse("relatorios/por_categoria.html", {
        "request": request, "current_user": current_user,
        "dados": dados, "data_inicio": di, "data_fim": df,
    })


@router.get("/por-centro-custo", response_class=HTMLResponse)
async def por_centro_custo(
    request: Request,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    formato: Optional[str] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    di, df = _parse_datas(data_inicio, data_fim)
    dados = relatorio_service.por_centro_custo(db, di, df)

    if formato == "pdf":
        headers = ["Centro de Custo", "Entradas (R$)", "Saídas (R$)", "Saldo (R$)"]
        rows = [[d["centro"].nome, f"{d['entradas']:.2f}", f"{d['saidas']:.2f}", f"{d['saldo']:.2f}"] for d in dados]
        pdf = export_service.export_pdf("Por Centro de Custo", headers, rows)
        return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=por_centro_custo.pdf"})
    if formato == "excel":
        headers = ["Centro de Custo", "Entradas (R$)", "Saídas (R$)", "Saldo (R$)"]
        rows = [[d["centro"].nome, float(d["entradas"]), float(d["saidas"]), float(d["saldo"])] for d in dados]
        xls = export_service.export_excel("Por Centro de Custo", headers, rows)
        return Response(xls, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=por_centro_custo.xlsx"})

    return templates.TemplateResponse("relatorios/por_centro_custo.html", {
        "request": request, "current_user": current_user,
        "dados": dados, "data_inicio": di, "data_fim": df,
    })


@router.get("/previsto-realizado", response_class=HTMLResponse)
async def previsto_realizado(
    request: Request,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    formato: Optional[str] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    di, df = _parse_datas(data_inicio, data_fim)
    dados = relatorio_service.previsto_vs_realizado(db, di, df)

    if formato == "pdf":
        headers = ["Categoria", "Previsto (R$)", "Realizado (R$)", "Diferença (R$)", "% Execução"]
        rows = [[d["categoria"].nome, f"{d['previsto']:.2f}", f"{d['realizado']:.2f}", f"{d['diferenca']:.2f}", f"{d['percentual']:.1f}%"] for d in dados]
        pdf = export_service.export_pdf("Previsto vs Realizado", headers, rows)
        return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=previsto_realizado.pdf"})
    if formato == "excel":
        headers = ["Categoria", "Previsto (R$)", "Realizado (R$)", "Diferença (R$)", "% Execução"]
        rows = [[d["categoria"].nome, float(d["previsto"]), float(d["realizado"]), float(d["diferenca"]), float(d["percentual"])] for d in dados]
        xls = export_service.export_excel("Previsto vs Realizado", headers, rows)
        return Response(xls, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=previsto_realizado.xlsx"})

    return templates.TemplateResponse("relatorios/previsto_realizado.html", {
        "request": request, "current_user": current_user,
        "dados": dados, "data_inicio": di, "data_fim": df,
    })


@router.get("/extrato-conta", response_class=HTMLResponse)
async def extrato_conta(
    request: Request,
    conta_id: Optional[int] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    formato: Optional[str] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    di, df = _parse_datas(data_inicio, data_fim)
    contas = db.query(Conta).filter(Conta.ativo == True).all()
    conta = None
    rows_data = []

    if conta_id:
        conta, rows_data = relatorio_service.extrato_conta(db, conta_id, di, df)

    if formato == "pdf" and conta_id:
        headers = ["Data", "Descrição", "Tipo", "Valor (R$)", "Saldo (R$)"]
        rows = [[r["transacao"].data_pagamento.strftime("%d/%m/%Y"), r["transacao"].descricao, r["transacao"].tipo, f"{r['transacao'].valor:.2f}", f"{r['saldo_corrente']:.2f}"] for r in rows_data]
        pdf = export_service.export_pdf(f"Extrato — {conta.nome}", headers, rows)
        return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=extrato.pdf"})
    if formato == "excel" and conta_id:
        headers = ["Data", "Descrição", "Tipo", "Valor (R$)", "Saldo (R$)"]
        rows = [[r["transacao"].data_pagamento.strftime("%d/%m/%Y"), r["transacao"].descricao, r["transacao"].tipo, float(r["transacao"].valor), float(r["saldo_corrente"])] for r in rows_data]
        xls = export_service.export_excel("Extrato", headers, rows)
        return Response(xls, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=extrato.xlsx"})

    return templates.TemplateResponse("relatorios/extrato_conta.html", {
        "request": request, "current_user": current_user,
        "contas": contas, "conta": conta, "rows_data": rows_data,
        "data_inicio": di, "data_fim": df, "conta_id": conta_id,
    })
