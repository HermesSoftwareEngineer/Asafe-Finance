from datetime import date
from decimal import Decimal
from io import BytesIO
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Conta, OfxImport, StatusConciliacao, Transacao, TipoLancamento, Usuario


def importar_ofx(
    conteudo: bytes,
    arquivo_nome: str,
    conta: Conta,
    usuario: Usuario,
    db: Session,
) -> dict:
    try:
        from ofxparse import OfxParser
        ofx = OfxParser.parse(BytesIO(conteudo))
    except Exception as e:
        raise ValueError(f"Erro ao processar arquivo OFX: {str(e)}")

    account = ofx.account
    transacoes = account.statement.transactions if account and account.statement else []

    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    importadas = 0
    duplicatas = 0

    for tx in transacoes:
        tx_date = tx.date.date() if hasattr(tx.date, "date") else tx.date
        if data_inicio is None or tx_date < data_inicio:
            data_inicio = tx_date
        if data_fim is None or tx_date > data_fim:
            data_fim = tx_date

        ofx_id = str(tx.id) if tx.id else None
        if ofx_id:
            existente = db.query(Transacao).filter(
                Transacao.conta_id == conta.id,
                Transacao.ofx_transaction_id == ofx_id,
            ).first()
            if existente:
                duplicatas += 1
                continue

        # OFX: positive amount = credit (entrada), negative = debit (saida)
        valor = Decimal(str(abs(tx.amount)))
        tipo = TipoLancamento.entrada if tx.amount >= 0 else TipoLancamento.saida

        nova = Transacao(
            descricao=tx.memo or tx.payee or "Importado via OFX",
            tipo=tipo,
            valor=valor,
            data_pagamento=tx_date,
            conta_id=conta.id,
            forma_pagamento="outro",
            status_conciliacao=StatusConciliacao.pendente,
            ofx_transaction_id=ofx_id,
            usuario_id=usuario.id,
        )
        db.add(nova)
        importadas += 1

    importacao = OfxImport(
        conta_id=conta.id,
        arquivo_nome=arquivo_nome,
        data_inicio=data_inicio,
        data_fim=data_fim,
        total_registros=importadas,
        usuario_id=usuario.id,
    )
    db.add(importacao)
    db.commit()

    return {"importadas": importadas, "duplicatas": duplicatas, "total": len(list(transacoes))}
