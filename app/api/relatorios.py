from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Conta, Usuario
from app.services import relatorio_service, export_service
from app.api.deps import get_current_user


router = APIRouter(prefix="/api/relatorios", tags=["relatorios"])


def _parse_datas(data_inicio, data_fim):
    hoje = date.today()
    di = data_inicio or hoje.replace(day=1)
    df = data_fim or hoje
    return di, df


@router.get("/fluxo-caixa")
def fluxo_caixa(
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    conta_id: Optional[int] = None,
    formato: Optional[str] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    di, df = _parse_datas(data_inicio, data_fim)
    dados = relatorio_service.fluxo_de_caixa(db, di, df, conta_id)

    if formato == "pdf":
        headers = ["Período", "Entradas (R$)", "Saídas (R$)", "Saldo (R$)", "Saldo Acumulado (R$)"]
        rows = [
            [r["periodo"], f"{r['entradas']:.2f}", f"{r['saidas']:.2f}", f"{r['saldo']:.2f}", f"{r['saldo_acumulado']:.2f}"]
            for r in dados
        ]
        pdf = export_service.export_pdf("Fluxo de Caixa", headers, rows)
        return Response(
            pdf, media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=fluxo_caixa.pdf"},
        )
    if formato == "excel":
        headers = ["Período", "Entradas (R$)", "Saídas (R$)", "Saldo (R$)", "Saldo Acumulado (R$)"]
        rows = [
            [r["periodo"], float(r["entradas"]), float(r["saidas"]), float(r["saldo"]), float(r["saldo_acumulado"])]
            for r in dados
        ]
        xls = export_service.export_excel("Fluxo de Caixa", headers, rows)
        return Response(
            xls,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=fluxo_caixa.xlsx"},
        )

    return {
        "data_inicio": di.isoformat(),
        "data_fim": df.isoformat(),
        "conta_id": conta_id,
        "items": [
            {
                "periodo": r["periodo"],
                "entradas": float(r["entradas"]),
                "saidas": float(r["saidas"]),
                "saldo": float(r["saldo"]),
                "saldo_acumulado": float(r["saldo_acumulado"]),
            }
            for r in dados
        ],
    }


@router.get("/por-categoria")
def por_categoria(
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    categoria_ids: Optional[List[int]] = Query(None),
    granularidade: str = Query("mes", regex="^(dia|semana|mes)$"),
    formato: Optional[str] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    di, df = _parse_datas(data_inicio, data_fim)
    dados = relatorio_service.por_categoria(db, di, df, categoria_ids, granularidade)

    if formato == "pdf":
        headers = ["Categoria", "Subcategoria", "Total (R$)"]
        rows = []
        for d in dados["categorias"]:
            if d["subcategorias"]:
                for s in d["subcategorias"]:
                    rows.append([d["categoria_nome"], s["categoria_nome"], f"{s['total']:.2f}"])
            else:
                rows.append([d["categoria_nome"], "-", f"{d['total']:.2f}"])
        pdf = export_service.export_pdf("Relatório por Categoria", headers, rows)
        return Response(
            pdf, media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=por_categoria.pdf"},
        )
    if formato == "excel":
        headers = ["Categoria", "Subcategoria", "Total (R$)"]
        rows = []
        for d in dados["categorias"]:
            if d["subcategorias"]:
                for s in d["subcategorias"]:
                    rows.append([d["categoria_nome"], s["categoria_nome"], float(s["total"])])
            else:
                rows.append([d["categoria_nome"], "-", float(d["total"])])
        xls = export_service.export_excel("Por Categoria", headers, rows)
        return Response(
            xls,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=por_categoria.xlsx"},
        )

    return {
        "data_inicio": di.isoformat(),
        "data_fim": df.isoformat(),
        "granularidade": granularidade,
        "filtros": {"categoria_ids": categoria_ids},
        "categorias": dados["categorias"],
        "pie": dados["pie"],
        "series": dados["series"],
    }


@router.get("/por-centro-custo")
def por_centro_custo(
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
        rows = [
            [d["centro"].nome, f"{d['entradas']:.2f}", f"{d['saidas']:.2f}", f"{d['saldo']:.2f}"]
            for d in dados
        ]
        pdf = export_service.export_pdf("Por Centro de Custo", headers, rows)
        return Response(
            pdf, media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=por_centro_custo.pdf"},
        )
    if formato == "excel":
        headers = ["Centro de Custo", "Entradas (R$)", "Saídas (R$)", "Saldo (R$)"]
        rows = [
            [d["centro"].nome, float(d["entradas"]), float(d["saidas"]), float(d["saldo"])]
            for d in dados
        ]
        xls = export_service.export_excel("Por Centro de Custo", headers, rows)
        return Response(
            xls,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=por_centro_custo.xlsx"},
        )

    return {
        "data_inicio": di.isoformat(),
        "data_fim": df.isoformat(),
        "items": [
            {
                "centro_id": d["centro"].id,
                "centro_nome": d["centro"].nome,
                "entradas": float(d["entradas"]),
                "saidas": float(d["saidas"]),
                "saldo": float(d["saldo"]),
            }
            for d in dados
        ],
    }


@router.get("/previsto-realizado")
def previsto_realizado(
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
        rows = [
            [
                d["categoria"].nome, f"{d['previsto']:.2f}", f"{d['realizado']:.2f}",
                f"{d['diferenca']:.2f}", f"{d['percentual']:.1f}%",
            ]
            for d in dados
        ]
        pdf = export_service.export_pdf("Previsto vs Realizado", headers, rows)
        return Response(
            pdf, media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=previsto_realizado.pdf"},
        )
    if formato == "excel":
        headers = ["Categoria", "Previsto (R$)", "Realizado (R$)", "Diferença (R$)", "% Execução"]
        rows = [
            [
                d["categoria"].nome, float(d["previsto"]), float(d["realizado"]),
                float(d["diferenca"]), float(d["percentual"]),
            ]
            for d in dados
        ]
        xls = export_service.export_excel("Previsto vs Realizado", headers, rows)
        return Response(
            xls,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=previsto_realizado.xlsx"},
        )

    return {
        "data_inicio": di.isoformat(),
        "data_fim": df.isoformat(),
        "items": [
            {
                "categoria_id": d["categoria"].id,
                "categoria_nome": d["categoria"].nome,
                "previsto": float(d["previsto"]),
                "realizado": float(d["realizado"]),
                "diferenca": float(d["diferenca"]),
                "percentual": float(d["percentual"]),
            }
            for d in dados
        ],
    }


@router.get("/extrato-conta")
def extrato_conta(
    conta_id: Optional[int] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    formato: Optional[str] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    di, df = _parse_datas(data_inicio, data_fim)

    if not conta_id:
        contas = db.query(Conta).filter(Conta.ativo == True).all()
        return {
            "conta": None,
            "data_inicio": di.isoformat(),
            "data_fim": df.isoformat(),
            "items": [],
            "contas_disponiveis": [
                {"id": c.id, "nome": c.nome, "tipo": c.tipo}
                for c in contas
            ],
        }

    conta, rows_data = relatorio_service.extrato_conta(db, conta_id, di, df)
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")

    if formato == "pdf":
        headers = ["Data", "Descrição", "Tipo", "Valor (R$)", "Saldo (R$)"]
        rows = [
            [
                r["lancamento"].data.strftime("%d/%m/%Y"),
                r["lancamento"].descricao,
                r["lancamento"].tipo,
                f"{r['lancamento'].valor_total:.2f}",
                f"{r['saldo_corrente']:.2f}",
            ]
            for r in rows_data
        ]
        pdf = export_service.export_pdf(f"Extrato — {conta.nome}", headers, rows)
        return Response(
            pdf, media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=extrato.pdf"},
        )
    if formato == "excel":
        headers = ["Data", "Descrição", "Tipo", "Valor (R$)", "Saldo (R$)"]
        rows = [
            [
                r["lancamento"].data.strftime("%d/%m/%Y"),
                r["lancamento"].descricao,
                r["lancamento"].tipo,
                float(r["lancamento"].valor_total),
                float(r["saldo_corrente"]),
            ]
            for r in rows_data
        ]
        xls = export_service.export_excel("Extrato", headers, rows)
        return Response(
            xls,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=extrato.xlsx"},
        )

    return {
        "conta": {"id": conta.id, "nome": conta.nome, "tipo": conta.tipo},
        "data_inicio": di.isoformat(),
        "data_fim": df.isoformat(),
        "items": [
            {
                "id": r["lancamento"].id,
                "descricao": r["lancamento"].descricao,
                "tipo": r["lancamento"].tipo,
                "valor_total": float(r["lancamento"].valor_total),
                "data": r["lancamento"].data.isoformat(),
                "saldo_corrente": float(r["saldo_corrente"]),
            }
            for r in rows_data
        ],
    }


@router.get("/saldo")
def saldo_contas(
    data_alvo: Optional[date] = None,
    conta_id: Optional[int] = None,
    formato: Optional[str] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dt = data_alvo or date.today()
    dados = relatorio_service.saldo_contas(db, dt, conta_id)

    if formato == "pdf":
        headers = ["Conta", "Tipo", "Saldo Inicial (R$)", "Entradas (R$)", "Saídas (R$)", "Saldo Atual (R$)"]
        rows = [
            [
                d["conta_nome"],
                d["conta_tipo"],
                f"{d['saldo_inicial']:.2f}",
                f"{d['entradas']:.2f}",
                f"{d['saidas']:.2f}",
                f"{d['saldo']:.2f}",
            ]
            for d in dados
        ]
        pdf = export_service.export_pdf(f"Saldo das Contas - {dt.strftime('%d/%m/%Y')}", headers, rows)
        return Response(
            pdf, media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=saldo_contas.pdf"},
        )
    if formato == "excel":
        headers = ["Conta", "Tipo", "Saldo Inicial (R$)", "Entradas (R$)", "Saídas (R$)", "Saldo Atual (R$)"]
        rows = [
            [
                d["conta_nome"],
                d["conta_tipo"],
                float(d["saldo_inicial"]),
                float(d["entradas"]),
                float(d["saidas"]),
                float(d["saldo"]),
            ]
            for d in dados
        ]
        xls = export_service.export_excel("Saldo das Contas", headers, rows)
        return Response(
            xls,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=saldo_contas.xlsx"},
        )

    return {
        "data_alvo": dt.isoformat(),
        "conta_id": conta_id,
        "saldo_total": float(sum(d["saldo"] for d in dados)),
        "items": [
            {
                "conta_id": d["conta_id"],
                "conta_nome": d["conta_nome"],
                "conta_tipo": d["conta_tipo"],
                "saldo_inicial": float(d["saldo_inicial"]),
                "entradas": float(d["entradas"]),
                "saidas": float(d["saidas"]),
                "saldo": float(d["saldo"]),
            }
            for d in dados
        ],
    }
