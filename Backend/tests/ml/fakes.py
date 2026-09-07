"""Estimador falso para testar a orquestração sem pagar o custo do treino real."""

import numpy as np


class EstimadorFake:
    """Determinístico: prevê a média do treino."""

    def __init__(self, *args, **kwargs):
        self.media = 0.0

    def fit(self, serie):
        serie = np.asarray(serie, dtype=float)
        self.media = float(serie.mean()) if serie.size else 0.0
        return self

    def prever(self, horizonte):
        return np.full(horizonte, self.media)


def fabrica_fake(algoritmo=None):
    return EstimadorFake()
