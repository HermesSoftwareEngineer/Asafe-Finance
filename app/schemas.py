from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


# --- Auth ---

class LoginForm(BaseModel):
    email: str
    password: str


class AlterarSenhaForm(BaseModel):
    senha_atual: str
    nova_senha: str
    confirmar_senha: str

    @field_validator("confirmar_senha")
    @classmethod
    def passwords_match(cls, v, info):
        if "nova_senha" in info.data and v != info.data["nova_senha"]:
            raise ValueError("As senhas não coincidem.")
        return v


# --- Conta ---

class ContaCreate(BaseModel):
    nome: str
    tipo: str
    saldo_inicial: Decimal = Decimal("0.00")
    ativo: bool = True


class ContaUpdate(ContaCreate):
    pass


# --- Categoria ---

class CategoriaCreate(BaseModel):
    nome: str
    tipo: str
    categoria_pai_id: Optional[int] = None
    cor: str = "#D4AF37"
    icone: Optional[str] = None
    ativo: bool = True


class CategoriaUpdate(CategoriaCreate):
    pass


# --- Centro de Custo ---

class CentroCustoCreate(BaseModel):
    nome: str
    ativo: bool = True


class CentroCustoUpdate(CentroCustoCreate):
    pass


# --- Lançamento ---

class LancamentoCreate(BaseModel):
    descricao: str
    tipo: str
    valor_total: Decimal
    data: date
    status: str = "a pagar"
    conta_id: int
    categoria_id: Optional[int] = None
    centro_custo_id: Optional[int] = None
    observacao: Optional[str] = None

    @field_validator("valor_total")
    @classmethod
    def valor_positivo(cls, v):
        if v <= 0:
            raise ValueError("O valor deve ser positivo.")
        return v

    @field_validator("status")
    @classmethod
    def status_valido(cls, v):
        if v not in {"pago", "a pagar"}:
            raise ValueError("status deve ser 'pago' ou 'a pagar'")
        return v


class LancamentoUpdate(LancamentoCreate):
    pass


# --- Usuário ---

class UsuarioCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    is_admin: bool = False
    ativo: bool = True


class UsuarioUpdate(BaseModel):
    nome: str
    email: EmailStr
    is_admin: bool = False
    ativo: bool = True
    nova_senha: Optional[str] = None
