from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user, hash_password, require_admin
from app.database import get_db
from app.models import Categoria, CentroCusto, Conta, TipoConta, TipoCategoria, Usuario
from app.templates_config import templates


router = APIRouter(prefix="/cadastros")


# ─── CONTAS ───────────────────────────────────────────────────────────────────

@router.get("/contas", response_class=HTMLResponse)
async def listar_contas(request: Request, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    contas = db.query(Conta).all()
    return templates.TemplateResponse("cadastros/contas.html", {"request": request, "current_user": current_user, "contas": contas, "error": None})


@router.post("/contas/novo")
async def criar_conta(
    request: Request,
    nome: str = Form(...),
    tipo: str = Form(...),
    saldo_inicial: float = Form(0.0),
    ativo: bool = Form(True),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conta = Conta(nome=nome, tipo=tipo, saldo_inicial=saldo_inicial, ativo=ativo)
    db.add(conta)
    db.commit()
    return RedirectResponse("/cadastros/contas", status_code=302)


@router.post("/contas/{conta_id}/editar")
async def editar_conta(
    conta_id: int,
    nome: str = Form(...),
    tipo: str = Form(...),
    saldo_inicial: float = Form(0.0),
    ativo: bool = Form(True),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conta = db.query(Conta).filter(Conta.id == conta_id).first()
    if not conta:
        raise HTTPException(404)
    conta.nome = nome
    conta.tipo = tipo
    conta.saldo_inicial = saldo_inicial
    conta.ativo = ativo
    db.commit()
    return RedirectResponse("/cadastros/contas", status_code=302)


@router.post("/contas/{conta_id}/excluir")
async def excluir_conta(conta_id: int, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    conta = db.query(Conta).filter(Conta.id == conta_id).first()
    if conta:
        db.delete(conta)
        db.commit()
    return RedirectResponse("/cadastros/contas", status_code=302)


# ─── CATEGORIAS ───────────────────────────────────────────────────────────────

@router.get("/categorias", response_class=HTMLResponse)
async def listar_categorias(request: Request, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    categorias = db.query(Categoria).filter(Categoria.categoria_pai_id == None).all()
    todas = db.query(Categoria).all()
    return templates.TemplateResponse("cadastros/categorias.html", {
        "request": request, "current_user": current_user,
        "categorias": categorias, "todas": todas, "error": None,
    })


@router.post("/categorias/novo")
async def criar_categoria(
    nome: str = Form(...),
    tipo: str = Form(...),
    categoria_pai_id: Optional[int] = Form(None),
    cor: str = Form("#D4AF37"),
    ativo: bool = Form(True),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Prevent 3rd level nesting
    if categoria_pai_id:
        pai = db.query(Categoria).filter(Categoria.id == categoria_pai_id).first()
        if pai and pai.categoria_pai_id is not None:
            raise HTTPException(400, "Máximo 2 níveis de categoria permitido.")
    cat = Categoria(nome=nome, tipo=tipo, categoria_pai_id=categoria_pai_id or None, cor=cor, ativo=ativo)
    db.add(cat)
    db.commit()
    return RedirectResponse("/cadastros/categorias", status_code=302)


@router.post("/categorias/{cat_id}/editar")
async def editar_categoria(
    cat_id: int,
    nome: str = Form(...),
    tipo: str = Form(...),
    categoria_pai_id: Optional[int] = Form(None),
    cor: str = Form("#D4AF37"),
    ativo: bool = Form(True),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cat = db.query(Categoria).filter(Categoria.id == cat_id).first()
    if not cat:
        raise HTTPException(404)
    cat.nome = nome
    cat.tipo = tipo
    cat.categoria_pai_id = categoria_pai_id or None
    cat.cor = cor
    cat.ativo = ativo
    db.commit()
    return RedirectResponse("/cadastros/categorias", status_code=302)


@router.post("/categorias/{cat_id}/excluir")
async def excluir_categoria(cat_id: int, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    cat = db.query(Categoria).filter(Categoria.id == cat_id).first()
    if cat:
        db.delete(cat)
        db.commit()
    return RedirectResponse("/cadastros/categorias", status_code=302)


# ─── CENTROS DE CUSTO ─────────────────────────────────────────────────────────

@router.get("/centros-custo", response_class=HTMLResponse)
async def listar_centros(request: Request, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    centros = db.query(CentroCusto).all()
    return templates.TemplateResponse("cadastros/centros_custo.html", {"request": request, "current_user": current_user, "centros": centros})


@router.post("/centros-custo/novo")
async def criar_centro(
    nome: str = Form(...),
    ativo: bool = Form(True),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.add(CentroCusto(nome=nome, ativo=ativo))
    db.commit()
    return RedirectResponse("/cadastros/centros-custo", status_code=302)


@router.post("/centros-custo/{centro_id}/editar")
async def editar_centro(
    centro_id: int,
    nome: str = Form(...),
    ativo: bool = Form(True),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = db.query(CentroCusto).filter(CentroCusto.id == centro_id).first()
    if not c:
        raise HTTPException(404)
    c.nome = nome
    c.ativo = ativo
    db.commit()
    return RedirectResponse("/cadastros/centros-custo", status_code=302)


@router.post("/centros-custo/{centro_id}/excluir")
async def excluir_centro(centro_id: int, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.query(CentroCusto).filter(CentroCusto.id == centro_id).first()
    if c:
        db.delete(c)
        db.commit()
    return RedirectResponse("/cadastros/centros-custo", status_code=302)


# ─── USUÁRIOS (admin only) ────────────────────────────────────────────────────

@router.get("/usuarios", response_class=HTMLResponse)
async def listar_usuarios(request: Request, admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    usuarios = db.query(Usuario).all()
    return templates.TemplateResponse("cadastros/usuarios.html", {
        "request": request, "current_user": admin, "usuarios": usuarios, "error": None,
    })


@router.post("/usuarios/novo")
async def criar_usuario(
    nome: str = Form(...),
    email: str = Form(...),
    senha: str = Form(...),
    is_admin: bool = Form(False),
    ativo: bool = Form(True),
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    existing = db.query(Usuario).filter(Usuario.email == email).first()
    if existing:
        raise HTTPException(400, "E-mail já cadastrado.")
    u = Usuario(nome=nome, email=email, senha_hash=hash_password(senha), is_admin=is_admin, ativo=ativo)
    db.add(u)
    db.commit()
    return RedirectResponse("/cadastros/usuarios", status_code=302)


@router.post("/usuarios/{usuario_id}/editar")
async def editar_usuario(
    usuario_id: int,
    nome: str = Form(...),
    email: str = Form(...),
    is_admin: bool = Form(False),
    ativo: bool = Form(True),
    nova_senha: Optional[str] = Form(None),
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not u:
        raise HTTPException(404)
    u.nome = nome
    u.email = email
    u.is_admin = is_admin
    u.ativo = ativo
    if nova_senha:
        u.senha_hash = hash_password(nova_senha)
    db.commit()
    return RedirectResponse("/cadastros/usuarios", status_code=302)


@router.post("/usuarios/{usuario_id}/excluir")
async def excluir_usuario(usuario_id: int, admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if u:
        db.delete(u)
        db.commit()
