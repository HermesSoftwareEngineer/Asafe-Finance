from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import authenticate_user, create_access_token, get_current_user, hash_password, verify_password
from app.database import get_db
from app.models import Usuario

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.cookies.get("access_token"):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
async def login(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, email, password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "E-mail ou senha incorretos."},
            status_code=401,
        )
    token = create_access_token({"sub": str(user.id), "email": user.email, "is_admin": user.is_admin})
    resp = RedirectResponse("/", status_code=302)
    resp.set_cookie("access_token", token, httponly=True, max_age=28800, samesite="lax")
    return resp


@router.post("/logout")
async def logout():
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie("access_token")
    return resp


@router.get("/alterar-senha", response_class=HTMLResponse)
async def alterar_senha_page(request: Request, current_user: Usuario = Depends(get_current_user)):
    return templates.TemplateResponse("alterar_senha.html", {"request": request, "current_user": current_user, "error": None, "success": None})


@router.post("/alterar-senha", response_class=HTMLResponse)
async def alterar_senha(
    request: Request,
    senha_atual: str = Form(...),
    nova_senha: str = Form(...),
    confirmar_senha: str = Form(...),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ctx = {"request": request, "current_user": current_user, "error": None, "success": None}
    if not verify_password(senha_atual, current_user.senha_hash):
        ctx["error"] = "Senha atual incorreta."
        return templates.TemplateResponse("alterar_senha.html", ctx)
    if nova_senha != confirmar_senha:
        ctx["error"] = "As novas senhas não coincidem."
        return templates.TemplateResponse("alterar_senha.html", ctx)
    if len(nova_senha) < 6:
        ctx["error"] = "A nova senha deve ter pelo menos 6 caracteres."
        return templates.TemplateResponse("alterar_senha.html", ctx)
    current_user.senha_hash = hash_password(nova_senha)
    db.commit()
    ctx["success"] = "Senha alterada com sucesso!"
    return templates.TemplateResponse("alterar_senha.html", ctx)
