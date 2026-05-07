from datetime import date, datetime
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
    data_competencia: date
    categoria_id: Optional[int] = None
    centro_custo_id: Optional[int] = None
    observacao: Optional[str] = None
    
    # Recorrência
    tipo_recorrencia: str = "unico"  # unico, fixo, parcelado
    frequencia_recorrencia: Optional[str] = None  # diario, semanal, quinzenal, mensal (para fixos)
    quantidade_parcelas: Optional[int] = None  # Para parcelados (ex: 12)

    @field_validator("valor_total")
    @classmethod
    def valor_positivo(cls, v):
        if v <= 0:
            raise ValueError("O valor deve ser positivo.")
        return v


class LancamentoUpdate(LancamentoCreate):
    pass


# --- Transação ---

class TransacaoCreate(BaseModel):
    descricao: str
    tipo: str
    valor: Decimal
    data_pagamento: date
    conta_id: int
    forma_pagamento: str
    status_conciliacao: str = "pendente"

    @field_validator("valor")
    @classmethod
    def valor_positivo(cls, v):
        if v <= 0:
            raise ValueError("O valor deve ser positivo.")
        return v


class TransacaoUpdate(TransacaoCreate):
    pass


# --- Vínculo ---

class VinculoCreate(BaseModel):
    lancamento_id: int
    transacao_id: int
    valor_vinculado: Decimal

    @field_validator("valor_vinculado")
    @classmethod
    def valor_positivo(cls, v):
        if v <= 0:
            raise ValueError("O valor deve ser positivo.")
        return v


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
