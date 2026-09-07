"""Elegibilidade de itens para previsão (RN06 e FA03) — funções puras.

Itens com histórico mensal abaixo do mínimo são omitidos do treino e devolvidos
com o motivo, para alimentar o aviso do FA03.
"""

from dataclasses import dataclass

import pandas as pd

MESES_MINIMOS = 3


@dataclass
class ItemOmitido:
    item_id: int
    meses_disponiveis: int
    motivo: str


def item_elegivel(serie: pd.DataFrame, meses_minimos: int = MESES_MINIMOS) -> bool:
    return len(serie) >= meses_minimos


def separar_elegiveis(
    series_por_item: dict[int, pd.DataFrame], meses_minimos: int = MESES_MINIMOS
) -> tuple[dict[int, pd.DataFrame], list[ItemOmitido]]:
    """Devolve (elegíveis, omitidos com o motivo)."""
    elegiveis: dict[int, pd.DataFrame] = {}
    omitidos: list[ItemOmitido] = []

    for item_id, serie in series_por_item.items():
        meses = len(serie)
        if meses >= meses_minimos:
            elegiveis[item_id] = serie
        else:
            omitidos.append(
                ItemOmitido(
                    item_id=item_id,
                    meses_disponiveis=meses,
                    motivo=(
                        f"Histórico insuficiente: {meses} mês(es) disponível(is), "
                        f"mínimo de {meses_minimos}."
                    ),
                )
            )

    return elegiveis, omitidos
