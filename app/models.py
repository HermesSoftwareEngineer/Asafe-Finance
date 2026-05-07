from datetime import date, datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum, ForeignKey,
    Integer, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TipoConta(str, PyEnum):
    corrente = "corrente"
    poupanca = "poupanca"
    caixa = "caixa"
    outro = "outro"


class TipoCategoria(str, PyEnum):
    entrada = "entrada"
    saida = "saida"


class TipoLancamento(str, PyEnum):
    entrada = "entrada"
    saida = "saida"


class StatusLancamento(str, PyEnum):
    previsto = "previsto"
    parcial = "parcial"
    realizado = "realizado"



class StatusConciliacao(str, PyEnum):
    pendente = "pendente"
    conciliado = "conciliado"
    ignorado = "ignorado"


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    senha_hash = Column(String(200), nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    lancamentos = relationship("Lancamento", back_populates="usuario")
    transacoes = relationship("Transacao", back_populates="usuario")
    ofx_imports = relationship("OfxImport", back_populates="usuario")


class Conta(Base):
    __tablename__ = "contas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    tipo = Column(Enum(TipoConta), nullable=False)
    saldo_inicial = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)

    transacoes = relationship("Transacao", back_populates="conta")
    ofx_imports = relationship("OfxImport", back_populates="conta")


class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    tipo = Column(Enum(TipoCategoria), nullable=False)
    categoria_pai_id = Column(Integer, ForeignKey("categorias.id"), nullable=True)
    cor = Column(String(7), default="#D4AF37")
    ativo = Column(Boolean, default=True, nullable=False)

    subcategorias = relationship("Categoria", back_populates="categoria_pai")
    categoria_pai = relationship("Categoria", back_populates="subcategorias", remote_side=[id])
    lancamentos = relationship("Lancamento", back_populates="categoria")


class CentroCusto(Base):
    __tablename__ = "centros_custo"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)

    lancamentos = relationship("Lancamento", back_populates="centro_custo")


class Lancamento(Base):
    __tablename__ = "lancamentos"

    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String(200), nullable=False)
    tipo = Column(Enum(TipoLancamento), nullable=False)
    valor_total = Column(Numeric(10, 2), nullable=False)
    data_competencia = Column(Date, nullable=False)
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=True)
    centro_custo_id = Column(Integer, ForeignKey("centros_custo.id"), nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    observacao = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    usuario = relationship("Usuario", back_populates="lancamentos")
    categoria = relationship("Categoria", back_populates="lancamentos")
    centro_custo = relationship("CentroCusto", back_populates="lancamentos")
    vinculos = relationship("LancamentoTransacao", back_populates="lancamento", cascade="all, delete-orphan")

    @property
    def valor_pago(self) -> Decimal:
        return sum(v.valor_vinculado for v in self.vinculos) if self.vinculos else Decimal("0.00")

    @property
    def status(self) -> str:
        pago = self.valor_pago
        if pago <= 0:
            return StatusLancamento.previsto
        elif pago >= self.valor_total:
            return StatusLancamento.realizado
        else:
            return StatusLancamento.parcial


class Transacao(Base):
    __tablename__ = "transacoes"

    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String(200), nullable=False)
    tipo = Column(Enum(TipoLancamento), nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)
    data_pagamento = Column(Date, nullable=False)
    conta_id = Column(Integer, ForeignKey("contas.id"), nullable=False)
    forma_pagamento = Column(String(50), nullable=False)
    status_conciliacao = Column(Enum(StatusConciliacao), default=StatusConciliacao.pendente, nullable=False)
    ofx_transaction_id = Column(String(100), nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    conta = relationship("Conta", back_populates="transacoes")
    usuario = relationship("Usuario", back_populates="transacoes")
    vinculos = relationship("LancamentoTransacao", back_populates="transacao", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("conta_id", "ofx_transaction_id", name="uq_ofx_transaction"),
    )


class LancamentoTransacao(Base):
    __tablename__ = "lancamento_transacao"

    id = Column(Integer, primary_key=True, index=True)
    lancamento_id = Column(Integer, ForeignKey("lancamentos.id"), nullable=False)
    transacao_id = Column(Integer, ForeignKey("transacoes.id"), nullable=False)
    valor_vinculado = Column(Numeric(10, 2), nullable=False)

    lancamento = relationship("Lancamento", back_populates="vinculos")
    transacao = relationship("Transacao", back_populates="vinculos")


class OfxImport(Base):
    __tablename__ = "ofx_imports"

    id = Column(Integer, primary_key=True, index=True)
    conta_id = Column(Integer, ForeignKey("contas.id"), nullable=False)
    arquivo_nome = Column(String(200), nullable=False)
    data_inicio = Column(Date, nullable=True)
    data_fim = Column(Date, nullable=True)
    total_registros = Column(Integer, default=0)
    importado_em = Column(DateTime, server_default=func.now())
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    conta = relationship("Conta", back_populates="ofx_imports")
    usuario = relationship("Usuario", back_populates="ofx_imports")
