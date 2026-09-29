"""Métodos de Croston para demanda intermitente.

Croston separa a série em (tamanho da demanda) e (intervalo entre demandas),
suaviza cada uma exponencialmente e prevê uma TAXA diária constante = nível /
intervalo. A variante SBA (Syntetos-Boylan Approximation) aplica o fator de
correção de viés (1 - alpha/2), recomendado para itens lumpy/intermitentes.

Referência: Syntetos & Boylan (2005).
"""

from __future__ import annotations

import numpy as np

ALPHA_PADRAO = 0.1


def croston(serie, *, alpha: float = ALPHA_PADRAO, variante: str = "sba") -> float:
    """Taxa de demanda diária prevista (constante) para uma série diária.

    ``variante``: "classico" (Croston) ou "sba" (correção de viés).
    Séries sem nenhuma demanda retornam 0.0.
    """
    y = np.asarray(serie, dtype=float)
    demandas = np.flatnonzero(y > 0)
    if demandas.size == 0:
        return 0.0

    nivel = float(y[demandas[0]])  # tamanho da demanda
    intervalos = np.diff(demandas)
    intervalo = float(intervalos.mean()) if intervalos.size else float(demandas[0] + 1)

    desde_ultima = 1
    for t in range(int(demandas[0]) + 1, y.size):
        if y[t] > 0:
            nivel = alpha * float(y[t]) + (1 - alpha) * nivel
            intervalo = alpha * desde_ultima + (1 - alpha) * intervalo
            desde_ultima = 1
        else:
            desde_ultima += 1

    if intervalo <= 0:
        return 0.0
    taxa = nivel / intervalo
    if variante == "sba":
        taxa *= 1 - alpha / 2
    return float(max(taxa, 0.0))
