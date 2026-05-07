from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import authenticate_user, create_access_token, verify_password, hash_password
from app.database import get_db
from app.models import Usuario
from app.api.deps import get_current_user


router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    email: str
    password: str


class AlterarSenhaBody(BaseModel):
    senha_atual: str
    nova_senha: str
    confirmar_senha: str


@router.post("/login")
def login(body: LoginBody, response: Response, db: Session = Depends(get_db)):
    user = authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    token = create_access_token({"sub": str(user.id)})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 480,
    )
    return {"id": user.id, "nome": user.nome, "email": user.email, "is_admin": user.is_admin}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"ok": True}


@router.get("/me")
def me(current_user: Usuario = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "nome": current_user.nome,
        "email": current_user.email,
        "is_admin": current_user.is_admin,
    }


@router.post("/alterar-senha")
def alterar_senha(
    body: AlterarSenhaBody,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.senha_atual, current_user.senha_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    if body.nova_senha != body.confirmar_senha:
        raise HTTPException(status_code=400, detail="Nova senha e confirmação não coincidem")
    if len(body.nova_senha) < 6:
        raise HTTPException(status_code=400, detail="A nova senha deve ter pelo menos 6 caracteres")
    current_user.senha_hash = hash_password(body.nova_senha)
    db.commit()
    return {"ok": True}
