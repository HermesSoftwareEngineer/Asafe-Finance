import calendar
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import Lancamento, StatusConciliacao

FREQUENCIAS_VALIDAS = {"diaria", "semanal", "quinzenal", "mensal"}


def proxima_data(base: date, frequencia: str) -> date:
    if frequencia == "diaria":
        return base + timedelta(days=1)
    if frequencia == "semanal":
        return base + timedelta(weeks=1)
    if frequencia == "quinzenal":
        return base + timedelta(days=15)
    if frequencia == "mensal":
        month = base.month % 12 + 1
        year = base.year + (base.month // 12)
        day = min(base.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)
    raise ValueError(f"Frequência inválida: {frequencia}")


def _raiz_da_serie(db: Session, lancamento_id: int) -> Optional[Lancamento]:
    l = db.query(Lancamento).filter(Lancamento.id == lancamento_id).first()
    if not l:
        return None
    return l if l.lancamento_pai_id is None else db.query(Lancamento).filter(
        Lancamento.id == l.lancamento_pai_id
    ).first()


def todos_da_serie(db: Session, lancamento_id: int) -> list[Lancamento]:
    raiz = _raiz_da_serie(db, lancamento_id)
    if not raiz:
        return []
    return db.query(Lancamento).filter(
        or_(Lancamento.id == raiz.id, Lancamento.lancamento_pai_id == raiz.id)
    ).order_by(Lancamento.data).all()


def _serie_completa(db: Session, lancamento_id: int):
    lanc = db.query(Lancamento).filter(Lancamento.id == lancamento_id).first()
    if not lanc:
        return None, []
    raiz = _raiz_da_serie(db, lancamento_id)
    if not raiz:
        return None, []
    serie = db.query(Lancamento).filter(
        or_(Lancamento.id == raiz.id, Lancamento.lancamento_pai_id == raiz.id)
    ).order_by(Lancamento.data).all()
    return raiz, serie


def futuros_da_serie(db: Session, lancamento_id: int) -> list[Lancamento]:
    raiz, serie = _serie_completa(db, lancamento_id)
    if not raiz:
        return []
    atual = db.query(Lancamento).filter(Lancamento.id == lancamento_id).first()
    if not atual:
        return []
    return [l for l in serie if l.data >= atual.data]


def promover_novo_raiz(db: Session, lancamento_id: int) -> None:
    raiz, serie = _serie_completa(db, lancamento_id)
    if not raiz or len(serie) <= 1:
        return
    novo_raiz = serie[1]
    novo_raiz.lancamento_pai_id = None
    for l in serie[2:]:
        l.lancamento_pai_id = novo_raiz.id


def gerar_parcelas(
    db: Session,
    pai: Lancamento,
    total_parcelas: int,
    frequencia: str,
) -> list[Lancamento]:
    pai.tipo_recorrencia = "parcelado"
    pai.frequencia_recorrencia = frequencia
    pai.total_parcelas = total_parcelas
    pai.numero_parcela = 1
    descricao_base = pai.descricao
    pai.descricao = f"{descricao_base} (1/{total_parcelas})"

    filhos = []
    data_atual = pai.data
    for i in range(2, total_parcelas + 1):
        data_atual = proxima_data(data_atual, frequencia)
        filho = Lancamento(
            descricao=f"{descricao_base} ({i}/{total_parcelas})",
            tipo=pai.tipo,
            valor_total=pai.valor_total,
            data=data_atual,
            status="a pagar",
            tipo_recorrencia="parcelado",
            frequencia_recorrencia=frequencia,
            total_parcelas=total_parcelas,
            numero_parcela=i,
            lancamento_pai_id=pai.id,
            categoria_id=pai.categoria_id,
            centro_custo_id=pai.centro_custo_id,
            conta_id=pai.conta_id,
            usuario_id=pai.usuario_id,
            observacao=pai.observacao,
        )
        db.add(filho)
        filhos.append(filho)

    return filhos


def gerar_proximo_fixo(db: Session, lancamento_id: int, usuario_id: int) -> Lancamento:
    raiz = _raiz_da_serie(db, lancamento_id)
    if not raiz:
        raise ValueError("Lançamento não encontrado")
    if raiz.tipo_recorrencia != "fixo":
        raise ValueError("Apenas lançamentos fixos podem gerar próxima ocorrência")

    ultimo = db.query(Lancamento).filter(
        or_(Lancamento.id == raiz.id, Lancamento.lancamento_pai_id == raiz.id)
    ).order_by(Lancamento.data.desc()).first()

    proximo = Lancamento(
        descricao=raiz.descricao,
        tipo=raiz.tipo,
        valor_total=raiz.valor_total,
        data=proxima_data(ultimo.data, raiz.frequencia_recorrencia),
        status="a pagar",
        tipo_recorrencia="fixo",
        frequencia_recorrencia=raiz.frequencia_recorrencia,
        lancamento_pai_id=raiz.id,
        categoria_id=raiz.categoria_id,
        centro_custo_id=raiz.centro_custo_id,
        conta_id=raiz.conta_id,
        usuario_id=usuario_id,
        observacao=raiz.observacao,
    )
    db.add(proximo)
    return proximo


def excluir_serie(db: Session, lancamento_id: int) -> int:
    todos = todos_da_serie(db, lancamento_id)
    for l in todos:
        db.delete(l)
    return len(todos)
