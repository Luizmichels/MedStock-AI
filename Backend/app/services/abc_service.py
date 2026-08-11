"""
Classificação ABC dos itens por empresa.
Classe A: primeiros 70% do valor acumulado de consumo.
Classe B: próximos 20% (70–90%).
Classe C: últimos 10% (90–100%).
Recalculado a cada importação bem-sucedida.
"""

import logging
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.consumo_tratado import ConsumoTratado
from app.models.classificacao_abc import ClassificacaoABC

logger = logging.getLogger(__name__)


def recalcular_abc(db: Session, empresa_id: int) -> None:
    consumo_por_item = (
        db.query(
            ConsumoTratado.item_id,
            func.sum(ConsumoTratado.quantidade_total).label("total"),
        )
        .filter(ConsumoTratado.empresa_id == empresa_id)
        .group_by(ConsumoTratado.item_id)
        .order_by(func.sum(ConsumoTratado.quantidade_total).desc())
        .all()
    )

    if not consumo_por_item:
        logger.info("Nenhum dado para classificação ABC empresa=%s", empresa_id)
        return

    total_geral = sum(r.total for r in consumo_por_item)
    if total_geral == 0:
        return

    acumulado = 0.0
    novas_classificacoes = []
    for row in consumo_por_item:
        acumulado += row.total
        percentual = acumulado / total_geral

        if percentual <= 0.70:
            classe = "A"
        elif percentual <= 0.90:
            classe = "B"
        else:
            classe = "C"

        novas_classificacoes.append(
            {
                "item_id": row.item_id,
                "classe": classe,
                "valor_acumulado_percentual": round(percentual * 100, 2),
            }
        )

    db.query(ClassificacaoABC).filter(ClassificacaoABC.empresa_id == empresa_id).delete()

    for nc in novas_classificacoes:
        db.add(
            ClassificacaoABC(
                empresa_id=empresa_id,
                item_id=nc["item_id"],
                classe=nc["classe"],
                valor_acumulado_percentual=nc["valor_acumulado_percentual"],
            )
        )

    db.commit()
    logger.info(
        "ABC recalculado empresa=%s total_itens=%s", empresa_id, len(novas_classificacoes)
    )
