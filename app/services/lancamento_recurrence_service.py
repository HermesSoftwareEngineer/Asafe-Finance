"""
Serviço para gerenciar lançamentos recorrentes (fixos e parcelados).
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import List

from sqlalchemy.orm import Session

from app.models import Lancamento, TipoRecorrencia, FrequenciaRecorrencia


def gerar_lancamentos_parcelados(
    lancamento_template: Lancamento,
    quantidade_parcelas: int,
    db: Session,
) -> List[Lancamento]:
    """
    Gera lançamentos parcelados a partir de um template.
    
    Exemplo: R$1200 em 12 parcelas → 12 lançamentos de R$100 cada
    As datas são incrementadas mensalmente.
    """
    lancamentos = []
    valor_parcela = lancamento_template.valor_total / quantidade_parcelas
    
    for numero_parcela in range(1, quantidade_parcelas + 1):
        # Incrementa a data de competência por mês a cada parcela
        data_competencia = lancamento_template.data_competencia + timedelta(days=30 * (numero_parcela - 1))
        
        novo_lancamento = Lancamento(
            descricao=f"{lancamento_template.descricao} (Parcela {numero_parcela}/{quantidade_parcelas})",
            tipo=lancamento_template.tipo,
            valor_total=valor_parcela,
            data_competencia=data_competencia,
            categoria_id=lancamento_template.categoria_id,
            centro_custo_id=lancamento_template.centro_custo_id,
            usuario_id=lancamento_template.usuario_id,
            observacao=lancamento_template.observacao,
            tipo_recorrencia=TipoRecorrencia.parcelado,
            numero_parcela=numero_parcela,
            lancamento_pai_id=lancamento_template.id,
        )
        db.add(novo_lancamento)
        lancamentos.append(novo_lancamento)
    
    db.commit()
    return lancamentos


def calcular_proxima_data(
    data_atual: date,
    frequencia: str,
) -> date:
    """
    Calcula a próxima data de competência baseada na frequência.
    """
    if frequencia == FrequenciaRecorrencia.diario:
        return data_atual + timedelta(days=1)
    elif frequencia == FrequenciaRecorrencia.semanal:
        return data_atual + timedelta(days=7)
    elif frequencia == FrequenciaRecorrencia.quinzenal:
        return data_atual + timedelta(days=15)
    elif frequencia == FrequenciaRecorrencia.mensal:
        # Incrementa 30 dias (simplificado)
        return data_atual + timedelta(days=30)
    return data_atual


def gerar_proximo_lancamento_fixo(
    lancamento_fixo: Lancamento,
    db: Session,
) -> Lancamento:
    """
    Gera o próximo lançamento de uma recorrência fixa.
    
    Exemplo: Um lançamento fixo de aluguel mensal gera uma nova instância no próximo mês.
    """
    if lancamento_fixo.tipo_recorrencia != TipoRecorrencia.fixo:
        raise ValueError("Este lançamento não é uma recorrência fixa.")
    
    proxima_data = calcular_proxima_data(
        lancamento_fixo.data_competencia,
        lancamento_fixo.frequencia_recorrencia,
    )
    
    novo_lancamento = Lancamento(
        descricao=lancamento_fixo.descricao,
        tipo=lancamento_fixo.tipo,
        valor_total=lancamento_fixo.valor_total,
        data_competencia=proxima_data,
        categoria_id=lancamento_fixo.categoria_id,
        centro_custo_id=lancamento_fixo.centro_custo_id,
        usuario_id=lancamento_fixo.usuario_id,
        observacao=lancamento_fixo.observacao,
        tipo_recorrencia=TipoRecorrencia.fixo,
        frequencia_recorrencia=lancamento_fixo.frequencia_recorrencia,
        lancamento_pai_id=lancamento_fixo.lancamento_pai_id or lancamento_fixo.id,
    )
    db.add(novo_lancamento)
    db.commit()
    db.refresh(novo_lancamento)
    return novo_lancamento
