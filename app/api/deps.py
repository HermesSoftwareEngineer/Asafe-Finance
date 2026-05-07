from fastapi import Depends, HTTPException, Request, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth import decode_token
from app.database import get_db
from app.models import Usuario


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Usuario:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    try:
        payload = decode_token(token)
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Token inválido")
    user = db.query(Usuario).filter(Usuario.id == user_id, Usuario.ativo == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    return user


def require_admin(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Requer administrador")
    return current_user
