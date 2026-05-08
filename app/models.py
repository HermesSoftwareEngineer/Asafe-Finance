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


class StatusConciliacao(str, PyEnum):
    pendente = "pendente"
    conciliado = "conciliado"
    ignorado = "ignorado"


class StatusOfxTransaction(str, PyEnum):
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
    ofx_imports = relationship("OfxImport", back_populates="usuario")


class Conta(Base):
    __tablename__ = "contas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    tipo = Column(Enum(TipoConta), nullable=False)
    saldo_inicial = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)

    lancamentos = relationship("Lancamento", back_populates="conta")
    ofx_imports = relationship("OfxImport", back_populates="conta")
    ofx_transactions = relationship("OfxTransaction", back_populates="conta")


class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    tipo = Column(Enum(TipoCategoria), nullable=False)
    categoria_pai_id = Column(Integer, ForeignKey("categorias.id"), nullable=True)
    cor = Column(String(7), default="#D4AF37")
    icone = Column(String(50), nullable=True)
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
    data = Column(Date, nullable=False)
    # status: "pago" ou "a pagar"
    status = Column(String(20), nullable=False, default="a pagar")
    # Recorrência: "unico" | "fixo" | "parcelado"
    tipo_recorrencia = Column(String(20), nullable=False, default="unico")
    # frequência para fixo e parcelado: "diaria" | "semanal" | "quinzenal" | "mensal"
    frequencia_recorrencia = Column(String(20), nullable=True)
    total_parcelas = Column(Integer, nullable=True)
    numero_parcela = Column(Integer, nullable=True)
    lancamento_pai_id = Column(Integer, ForeignKey("lancamentos.id"), nullable=True)
    status_conciliacao = Column(Enum(StatusConciliacao), nullable=True)
    ofx_transaction_id = Column(String(100), nullable=True)
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=True)
    centro_custo_id = Column(Integer, ForeignKey("centros_custo.id"), nullable=True)
    conta_id = Column(Integer, ForeignKey("contas.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    observacao = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    usuario = relationship("Usuario", back_populates="lancamentos")
    categoria = relationship("Categoria", back_populates="lancamentos")
    centro_custo = relationship("CentroCusto", back_populates="lancamentos")
    conta = relationship("Conta", back_populates="lancamentos")
    ofx_transaction = relationship("OfxTransaction", back_populates="lancamento", uselist=False)
    lancamento_pai = relationship("Lancamento", remote_side="Lancamento.id", backref="parcelas")


class OfxImport(Base):
    __tablename__ = "ofx_imports"

    id = Column(Integer, primary_key=True, index=True)
    conta_id = Column(Integer, ForeignKey("contas.id"), nullable=False)
    arquivo_nome = Column(String(200), nullable=False)
    data_inicio = Column(Date, nullable=True)
    data_fim = Column(Date, nullable=True)
    total_registros = Column(Integer, default=0)
    novos_registros = Column(Integer, default=0)
    importado_em = Column(DateTime, server_default=func.now())
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    conta = relationship("Conta", back_populates="ofx_imports")
    usuario = relationship("Usuario", back_populates="ofx_imports")
    transactions = relationship("OfxTransaction", back_populates="ofx_import")


class OfxTransaction(Base):
    __tablename__ = "ofx_transactions"

    id = Column(Integer, primary_key=True, index=True)
    ofx_import_id = Column(Integer, ForeignKey("ofx_imports.id"), nullable=False)
    conta_id = Column(Integer, ForeignKey("contas.id"), nullable=False)
    data = Column(Date, nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)
    tipo = Column(Enum(TipoLancamento), nullable=False)
    descricao = Column(String(500), nullable=False)
    ofx_transaction_id = Column(String(100), nullable=False)
    status = Column(Enum(StatusOfxTransaction), default=StatusOfxTransaction.pendente, nullable=False)
    lancamento_id = Column(Integer, ForeignKey("lancamentos.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    ofx_import = relationship("OfxImport", back_populates="transactions")
    conta = relationship("Conta", back_populates="ofx_transactions")
    lancamento = relationship("Lancamento", back_populates="ofx_transaction")

    __table_args__ = (
        UniqueConstraint("conta_id", "ofx_transaction_id", name="uq_ofx_tx_conta"),
    )
