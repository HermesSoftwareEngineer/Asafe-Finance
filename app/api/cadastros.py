from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.database import get_db
from app.models import Categoria, CentroCusto, Conta, Usuario
from app.api.deps import get_current_user, require_admin


router = APIRouter(prefix="/api/cadastros", tags=["cadastros"])


# ─── PYDANTIC BODIES ──────────────────────────────────────────────────────────

class ContaBody(BaseModel):
    nome: str
    tipo: str
    saldo_inicial: float = 0.0
    ativo: bool = True


class CategoriaBody(BaseModel):
    nome: str
    tipo: str
    cor: str = "#D4AF37"
    categoria_pai_id: Optional[int] = None
    ativo: bool = True


class CentroCustoBody(BaseModel):
    nome: str
    ativo: bool = True


class UsuarioCreateBody(BaseModel):
    nome: str
    email: str
    senha: str
    is_admin: bool = False
    ativo: bool = True


class UsuarioUpdateBody(BaseModel):
    nome: str
    email: str
    is_admin: bool = False
    ativo: bool = True
    nova_senha: Optional[str] = None


# ─── CONTAS ───────────────────────────────────────────────────────────────────

def _conta_to_dict(conta: Conta) -> dict:
    return {
        "id": conta.id,
        "nome": conta.nome,
        "tipo": conta.tipo,
        "saldo_inicial": float(conta.saldo_inicial),
        "ativo": conta.ativo,
    }


@router.get("/contas")
def listar_contas(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contas = db.query(Conta).all()
    return [_conta_to_dict(c) for c in contas]


@router.post("/contas")
def criar_conta(
    body: ContaBody,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conta = Conta(nome=body.nome, tipo=body.tipo, saldo_inicial=body.saldo_inicial, ativo=body.ativo)
    db.add(conta)
    db.commit()
    db.refresh(conta)
    return _conta_to_dict(conta)


@router.put("/contas/{conta_id}")
def editar_conta(
    conta_id: int,
    body: ContaBody,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conta = db.query(Conta).filter(Conta.id == conta_id).first()
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    conta.nome = body.nome
    conta.tipo = body.tipo
    conta.saldo_inicial = body.saldo_inicial
    conta.ativo = body.ativo
    db.commit()
    db.refresh(conta)
    return _conta_to_dict(conta)


@router.delete("/contas/{conta_id}")
def excluir_conta(
    conta_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conta = db.query(Conta).filter(Conta.id == conta_id).first()
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    db.delete(conta)
    db.commit()
    return {"ok": True}


# ─── CATEGORIAS ───────────────────────────────────────────────────────────────

def _categoria_to_dict(cat: Categoria, include_subcategorias: bool = True) -> dict:
    result = {
        "id": cat.id,
        "nome": cat.nome,
        "tipo": cat.tipo,
        "cor": cat.cor,
        "ativo": cat.ativo,
        "categoria_pai_id": cat.categoria_pai_id,
    }
    if include_subcategorias:
        result["subcategorias"] = [
            _categoria_to_dict(sub, include_subcategorias=False)
            for sub in cat.subcategorias
        ]
    return result


@router.get("/categorias")
def listar_categorias(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    categorias = db.query(Categoria).filter(Categoria.categoria_pai_id == None).all()
    return [_categoria_to_dict(c) for c in categorias]


@router.post("/categorias")
def criar_categoria(
    body: CategoriaBody,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.categoria_pai_id:
        pai = db.query(Categoria).filter(Categoria.id == body.categoria_pai_id).first()
        if not pai:
            raise HTTPException(status_code=404, detail="Categoria pai não encontrada")
        if pai.categoria_pai_id is not None:
            raise HTTPException(status_code=400, detail="Máximo 2 níveis de categoria permitido")
    cat = Categoria(
        nome=body.nome,
        tipo=body.tipo,
        cor=body.cor,
        categoria_pai_id=body.categoria_pai_id or None,
        ativo=body.ativo,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return _categoria_to_dict(cat)


@router.put("/categorias/{cat_id}")
def editar_categoria(
    cat_id: int,
    body: CategoriaBody,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cat = db.query(Categoria).filter(Categoria.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    if body.categoria_pai_id:
        pai = db.query(Categoria).filter(Categoria.id == body.categoria_pai_id).first()
        if not pai:
            raise HTTPException(status_code=404, detail="Categoria pai não encontrada")
        if pai.categoria_pai_id is not None:
            raise HTTPException(status_code=400, detail="Máximo 2 níveis de categoria permitido")
    cat.nome = body.nome
    cat.tipo = body.tipo
    cat.cor = body.cor
    cat.categoria_pai_id = body.categoria_pai_id or None
    cat.ativo = body.ativo
    db.commit()
    db.refresh(cat)
    return _categoria_to_dict(cat)


@router.delete("/categorias/{cat_id}")
def excluir_categoria(
    cat_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cat = db.query(Categoria).filter(Categoria.id == cat_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    db.delete(cat)
    db.commit()
    return {"ok": True}


# ─── CENTROS DE CUSTO ─────────────────────────────────────────────────────────

def _centro_to_dict(c: CentroCusto) -> dict:
    return {"id": c.id, "nome": c.nome, "ativo": c.ativo}


@router.get("/centros-custo")
def listar_centros(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    centros = db.query(CentroCusto).all()
    return [_centro_to_dict(c) for c in centros]


@router.post("/centros-custo")
def criar_centro(
    body: CentroCustoBody,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = CentroCusto(nome=body.nome, ativo=body.ativo)
    db.add(c)
    db.commit()
    db.refresh(c)
    return _centro_to_dict(c)


@router.put("/centros-custo/{centro_id}")
def editar_centro(
    centro_id: int,
    body: CentroCustoBody,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = db.query(CentroCusto).filter(CentroCusto.id == centro_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Centro de custo não encontrado")
    c.nome = body.nome
    c.ativo = body.ativo
    db.commit()
    db.refresh(c)
    return _centro_to_dict(c)


@router.delete("/centros-custo/{centro_id}")
def excluir_centro(
    centro_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    c = db.query(CentroCusto).filter(CentroCusto.id == centro_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Centro de custo não encontrado")
    db.delete(c)
    db.commit()
    return {"ok": True}


# ─── USUÁRIOS (admin only) ────────────────────────────────────────────────────

def _usuario_to_dict(u: Usuario) -> dict:
    return {
        "id": u.id,
        "nome": u.nome,
        "email": u.email,
        "is_admin": u.is_admin,
        "ativo": u.ativo,
    }


@router.get("/usuarios")
def listar_usuarios(
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    usuarios = db.query(Usuario).all()
    return [_usuario_to_dict(u) for u in usuarios]


@router.post("/usuarios")
def criar_usuario(
    body: UsuarioCreateBody,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    existing = db.query(Usuario).filter(Usuario.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    u = Usuario(
        nome=body.nome,
        email=body.email,
        senha_hash=hash_password(body.senha),
        is_admin=body.is_admin,
        ativo=body.ativo,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return _usuario_to_dict(u)


@router.put("/usuarios/{usuario_id}")
def editar_usuario(
    usuario_id: int,
    body: UsuarioUpdateBody,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    u.nome = body.nome
    u.email = body.email
    u.is_admin = body.is_admin
    u.ativo = body.ativo
    if body.nova_senha:
        u.senha_hash = hash_password(body.nova_senha)
    db.commit()
    db.refresh(u)
    return _usuario_to_dict(u)


@router.delete("/usuarios/{usuario_id}")
def excluir_usuario(
    usuario_id: int,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    db.delete(u)
    db.commit()
    return {"ok": True}
