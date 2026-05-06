from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    Categoria, CentroCusto, Lancamento, LancamentoTransacao,
    TipoLancamento, Transacao, Usuario,
)

router = APIRouter(prefix="/lancamentos")
templates = Jinja2Templates(directory="app/templates")


def _get_categorias_folha(db: Session, tipo: Optional[str] = None):
    """Return leaf categories (those without children), optionally filtered by type."""
    q = db.query(Categoria).filter(Categoria.ativo == True)
    if tipo:
        q = q.filter(Categoria.tipo == tipo)
    todas = q.all()
    ids_pai = {c.categoria_pai_id for c in todas if c.categoria_pai_id}
    return [c for c in todas if c.id not in ids_pai]


def _get_categorias_grouped(db: Session, tipo: Optional[str] = None):
    """Return categories grouped by parent for select optgroups."""
    q = db.query(Categoria).filter(Categoria.ativo == True)
    if tipo:
        q = q.filter(Categoria.tipo == tipo)
    todas = q.all()
    pais = [c for c in todas if c.categoria_pai_id is None]
    grupos = []
    for pai in pais:
        filhos = [c for c in todas if c.categoria_pai_id == pai.id]
        if filhos:
            grupos.append({"pai": pai, "filhos": filhos})
        # if parent has no children, it can be selected directly
        else:
            grupos.append({"pai": None, "filhos": [pai]})
    return grupos


@router.get("", response_class=HTMLResponse)
async def listar_lancamentos(
    request: Request,
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
    per_page = 20
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
    lancamentos = q.offset((page - 1) * per_page).limit(per_page).all()

    # Filter by status (computed property — filter in Python)
    if status:
        lancamentos = [l for l in lancamentos if l.status == status]

    categorias = db.query(Categoria).filter(Categoria.ativo == True).all()
    centros = db.query(CentroCusto).filter(CentroCusto.ativo == True).all()

    return templates.TemplateResponse("lancamentos/lista.html", {
        "request": request,
        "current_user": current_user,
        "lancamentos": lancamentos,
        "categorias": categorias,
        "centros": centros,
        "page": page,
        "total": total,
        "per_page": per_page,
        "filtros": {
            "tipo": tipo, "status": status, "categoria_id": categoria_id,
            "centro_custo_id": centro_custo_id, "data_inicio": data_inicio, "data_fim": data_fim,
        },
    })


@router.get("/novo", response_class=HTMLResponse)
async def form_novo(
    request: Request,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    grupos = _get_categorias_grouped(db)
    centros = db.query(CentroCusto).filter(CentroCusto.ativo == True).all()
    return templates.TemplateResponse("lancamentos/form.html", {
        "request": request,
        "current_user": current_user,
        "lancamento": None,
        "grupos_categorias": grupos,
        "centros": centros,
        "error": None,
    })


@router.post("/novo", response_class=HTMLResponse)
async def criar_lancamento(
    request: Request,
    descricao: str = Form(...),
    tipo: str = Form(...),
    valor_total: Decimal = Form(...),
    data_competencia: date = Form(...),
    categoria_id: Optional[int] = Form(None),
    centro_custo_id: Optional[int] = Form(None),
    observacao: Optional[str] = Form(None),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    grupos = _get_categorias_grouped(db)
    centros = db.query(CentroCusto).filter(CentroCusto.ativo == True).all()
    ctx = {
        "request": request, "current_user": current_user,
        "lancamento": None, "grupos_categorias": grupos, "centros": centros, "error": None,
    }
    if valor_total <= 0:
        ctx["error"] = "O valor deve ser maior que zero."
        return templates.TemplateResponse("lancamentos/form.html", ctx)

    lancamento = Lancamento(
        descricao=descricao, tipo=tipo, valor_total=valor_total,
        data_competencia=data_competencia, categoria_id=categoria_id or None,
        centro_custo_id=centro_custo_id or None, observacao=observacao,
        usuario_id=current_user.id,
    )
    db.add(lancamento)
    db.commit()
    db.refresh(lancamento)

    hx = request.headers.get("HX-Request")
    if hx:
        return HTMLResponse('<div id="modal-container"></div><script>window.location.reload();</script>')
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/lancamentos", status_code=302)


@router.get("/{lancamento_id}/editar", response_class=HTMLResponse)
async def form_editar(
    lancamento_id: int,
    request: Request,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lancamento = db.query(Lancamento).filter(Lancamento.id == lancamento_id).first()
    if not lancamento:
        raise HTTPException(404, "Lançamento não encontrado.")
    grupos = _get_categorias_grouped(db)
    centros = db.query(CentroCusto).filter(CentroCusto.ativo == True).all()
    return templates.TemplateResponse("lancamentos/form.html", {
        "request": request, "current_user": current_user,
        "lancamento": lancamento, "grupos_categorias": grupos, "centros": centros, "error": None,
    })


@router.post("/{lancamento_id}/editar", response_class=HTMLResponse)
async def editar_lancamento(
    lancamento_id: int,
    request: Request,
    descricao: str = Form(...),
    tipo: str = Form(...),
    valor_total: Decimal = Form(...),
    data_competencia: date = Form(...),
    categoria_id: Optional[int] = Form(None),
    centro_custo_id: Optional[int] = Form(None),
    observacao: Optional[str] = Form(None),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lancamento = db.query(Lancamento).filter(Lancamento.id == lancamento_id).first()
    if not lancamento:
        raise HTTPException(404)

    lancamento.descricao = descricao
    lancamento.tipo = tipo
    lancamento.valor_total = valor_total
    lancamento.data_competencia = data_competencia
    lancamento.categoria_id = categoria_id or None
    lancamento.centro_custo_id = centro_custo_id or None
    lancamento.observacao = observacao
    db.commit()

    hx = request.headers.get("HX-Request")
    if hx:
        return HTMLResponse('<div id="modal-container"></div><script>window.location.reload();</script>')
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/lancamentos", status_code=302)


@router.post("/{lancamento_id}/excluir")
async def excluir_lancamento(
    lancamento_id: int,
    request: Request,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lancamento = db.query(Lancamento).filter(Lancamento.id == lancamento_id).first()
    if lancamento:
        db.delete(lancamento)
        db.commit()
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/lancamentos", status_code=302)


@router.get("/{lancamento_id}/vinculos", response_class=HTMLResponse)
async def vinculos_lancamento(
    lancamento_id: int,
    request: Request,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lancamento = db.query(Lancamento).filter(Lancamento.id == lancamento_id).first()
    if not lancamento:
        raise HTTPException(404)
    return templates.TemplateResponse("lancamentos/vinculos.html", {
        "request": request, "current_user": current_user, "lancamento": lancamento,
    })
