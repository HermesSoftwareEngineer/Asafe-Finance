from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Usuario

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Usuario:
    token = request.cookies.get("access_token")
    credentials_exc = HTTPException(
        status_code=status.HTTP_302_FOUND,
        headers={"Location": "/login"},
    )
    if not token:
        raise credentials_exc
    try:
        payload = decode_token(token)
        user_id: int = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise credentials_exc

    user = db.query(Usuario).filter(Usuario.id == user_id, Usuario.ativo == True).first()
    if not user:
        raise credentials_exc
    return user


def require_admin(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Acesso negado: privilégios de administrador necessários.")
    return current_user


def authenticate_user(db: Session, email: str, password: str) -> Optional[Usuario]:
    user = db.query(Usuario).filter(Usuario.email == email, Usuario.ativo == True).first()
    if not user or not verify_password(password, user.senha_hash):
        return None
    return user
