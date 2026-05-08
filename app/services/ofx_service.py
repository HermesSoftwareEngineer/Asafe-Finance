from datetime import date, timedelta
from decimal import Decimal
from difflib import SequenceMatcher
from io import BytesIO
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Lancamento, OfxImport, OfxTransaction, StatusOfxTransaction


def _similaridade(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _score_match(ofx_valor: Decimal, ofx_data: date, ofx_descricao: str,
                 l_valor: Decimal, l_data: date, l_descricao: str) -> float:
    score = 0.0

    # Valor: 50% do peso
    diff = abs(float(ofx_valor) - float(l_valor))
    if diff < 0.01:
        score += 0.5
    elif diff < 1.0:
        score += 0.25
    elif diff < 5.0:
        score += 0.1

    # Data: 40% do peso
    date_diff = abs((ofx_data - l_data).days)
    if date_diff == 0:
        score += 0.4
    elif date_diff == 1:
        score += 0.2
    elif date_diff <= 3:
        score += 0.05

    # Descrição: 10% do peso
    score += _similaridade(ofx_descricao, l_descricao) * 0.1

    return score


def buscar_matches(db: Session, ofx_t: OfxTransaction, limite: int = 5) -> list[dict]:
    janela = timedelta(days=7)
    lancamentos = db.query(Lancamento).filter(
        Lancamento.conta_id == ofx_t.conta_id,
        Lancamento.tipo == ofx_t.tipo,
        Lancamento.status == "pago",
        Lancamento.data >= ofx_t.data - janela,
        Lancamento.data <= ofx_t.data + janela,
        Lancamento.ofx_transaction_id == None,
    ).all()

    scored = []
    for l in lancamentos:
        score = _score_match(ofx_t.valor, ofx_t.data, ofx_t.descricao,
                             l.valor_total, l.data, l.descricao)
        if score >= 0.3:
            scored.append({"lancamento": l, "score": round(score, 3)})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limite]


def importar_ofx(
    db: Session,
    content: bytes,
    conta_id: int,
    usuario_id: int,
    arquivo_nome: str,
) -> dict:
    try:
        from ofxparse import OfxParser
        ofx = OfxParser.parse(BytesIO(content))
    except Exception as e:
        raise ValueError(f"Arquivo OFX inválido ou não suportado: {e}")

    try:
        statement = ofx.account.statement
        raw_txs = statement.transactions
        data_inicio = statement.start_date.date() if statement.start_date else None
        data_fim = statement.end_date.date() if statement.end_date else None
    except AttributeError as e:
        raise ValueError(f"Estrutura OFX inesperada: {e}")

    ofx_import = OfxImport(
        conta_id=conta_id,
        arquivo_nome=arquivo_nome,
        data_inicio=data_inicio,
        data_fim=data_fim,
        total_registros=len(raw_txs),
        novos_registros=0,
        usuario_id=usuario_id,
    )
    db.add(ofx_import)
    db.flush()

    novos = 0
    duplicatas = 0
    for tx in raw_txs:
        ofx_id = str(tx.id)

        existe = db.query(OfxTransaction).filter(
            OfxTransaction.conta_id == conta_id,
            OfxTransaction.ofx_transaction_id == ofx_id,
        ).first()
        if existe:
            duplicatas += 1
            continue

        valor = Decimal(str(tx.amount))
        tipo = "entrada" if valor > 0 else "saida"
        descricao = (getattr(tx, "memo", None) or getattr(tx, "payee", None) or "Sem descrição").strip()
        data_tx = tx.date.date() if hasattr(tx.date, "date") else tx.date

        db.add(OfxTransaction(
            ofx_import_id=ofx_import.id,
            conta_id=conta_id,
            data=data_tx,
            valor=abs(valor),
            tipo=tipo,
            descricao=descricao,
            ofx_transaction_id=ofx_id,
            status=StatusOfxTransaction.pendente,
        ))
        novos += 1

    ofx_import.novos_registros = novos
    db.commit()
    db.refresh(ofx_import)

    return {
        "ofx_import_id": ofx_import.id,
        "total_registros": ofx_import.total_registros,
        "novos_registros": novos,
        "duplicatas_ignoradas": duplicatas,
        "data_inicio": data_inicio.isoformat() if data_inicio else None,
        "data_fim": data_fim.isoformat() if data_fim else None,
    }
