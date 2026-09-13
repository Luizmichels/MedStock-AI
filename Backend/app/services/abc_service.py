"""
Classificação ABC dos itens por empresa.
Classe A: primeiros 70% do valor acumulado de consumo.
Classe B: próximos 20% (70–90%).
Classe C: últimos 10% (90–100%).
Recalculado a cada importação bem-sucedida.
"""

import logging

import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.consumo_tratado import ConsumoTratado
from app.models.classificacao_abc import ClassificacaoABC

logger = logging.getLogger(__name__)


def recalcular_abc(db: Session, empresa_id: int) -> None:
    """Classifica os itens da empresa em A/B/C pelo VALOR acumulado de consumo (RN05)."""
    consumo_por_item = (
        db.query(
            ConsumoTratado.item_id,
            func.sum(ConsumoTratado.valor_total).label("total"),
        )
        .filter(ConsumoTratado.empresa_id == empresa_id)
        .group_by(ConsumoTratado.item_id)
        .order_by(func.sum(ConsumoTratado.valor_total).desc())
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
        # A faixa é decidida pelo ponto em que o item COMEÇA no acumulado, para
        # que o item mais valioso seja sempre A mesmo quando sozinho concentra
        # mais de 70% do valor (RN05).
        percentual_inicial = acumulado / total_geral
        acumulado += row.total
        percentual_acumulado = acumulado / total_geral

        if percentual_inicial < 0.70:
            classe = "A"
        elif percentual_inicial < 0.90:
            classe = "B"
        else:
            classe = "C"

        novas_classificacoes.append(
            {
                "item_id": row.item_id,
                "classe": classe,
                "valor_acumulado_percentual": round(percentual_acumulado * 100, 2),
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


# --------------------------------------------------------------------------- #
# Classificação XYZ (RF05) — variabilidade da demanda pelo coeficiente de variação
# --------------------------------------------------------------------------- #
def _coeficiente_variacao(valores) -> float:
    arr = np.asarray(valores, dtype=float)
    if arr.size == 0:
        return float("inf")
    media = arr.mean()
    if media == 0:
        return float("inf")
    return float(arr.std() / media)


def classe_xyz(cv: float) -> str:
    """X = previsível (CV<=0.5), Y = intermediário (<=1.0), Z = errático (>1.0)."""
    if cv <= 0.5:
        return "X"
    if cv <= 1.0:
        return "Y"
    return "Z"


def classificar_xyz(db: Session, empresa_id: int) -> dict[int, str]:
    """Classe XYZ por item, a partir da variabilidade do consumo mensal."""
    linhas = (
        db.query(
            ConsumoTratado.item_id,
            ConsumoTratado.periodo,
            func.sum(ConsumoTratado.quantidade_total),
        )
        .filter(ConsumoTratado.empresa_id == empresa_id)
        .group_by(ConsumoTratado.item_id, ConsumoTratado.periodo)
        .all()
    )
    series: dict[int, list[float]] = {}
    for item_id, _periodo, quantidade in linhas:
        series.setdefault(item_id, []).append(float(quantidade))
    return {item_id: classe_xyz(_coeficiente_variacao(v)) for item_id, v in series.items()}


def matriz_abc_xyz(db: Session, empresa_id: int) -> dict[str, int]:
    """Contagem de itens por classe combinada (ex.: 'AX', 'BZ'), cruzando ABC e XYZ."""
    abc = {
        c.item_id: c.classe
        for c in db.query(ClassificacaoABC).filter(ClassificacaoABC.empresa_id == empresa_id).all()
    }
    xyz = classificar_xyz(db, empresa_id)
    combinada: dict[str, int] = {}
    for item_id, classe_abc in abc.items():
        chave = classe_abc + xyz.get(item_id, "Z")
        combinada[chave] = combinada.get(chave, 0) + 1
    return combinada
