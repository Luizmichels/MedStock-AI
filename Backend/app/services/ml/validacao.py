from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import numpy as np

from app.services.ml import metrics
from app.services.ml.estimadores import ALGORITMOS, Estimador, criar


@dataclass
class ResultadoAvaliacao:
    algoritmo: str
    mae: float
    rmse: float
    mape: float


def walk_forward(
    serie,
    fabrica_estimador: Callable[[], Estimador],
    *,
    n_dobras: int = 3,
    horizonte: int = 1,
) -> dict:
    """Treino expansivo; a cada dobra prevê os próximos ``horizonte`` meses.

    ``fabrica_estimador`` é um callable sem argumentos que devolve um estimador
    novo (com ``fit``/``prever``) — assim cada dobra re-treina do zero.
    """
    valores = np.asarray(serie, dtype=float)
    n = len(valores)

    total_teste = n_dobras * horizonte
    if n <= total_teste:
        n_dobras = max((n - 1) // horizonte, 1)
        total_teste = n_dobras * horizonte

    inicio_teste = n - total_teste
    y_real: list[float] = []
    y_prev: list[float] = []

    for k in range(n_dobras):
        corte = inicio_teste + k * horizonte
        treino = valores[:corte]
        teste = valores[corte:corte + horizonte]
        if treino.size == 0 or teste.size == 0:
            continue
        estimador = fabrica_estimador()
        estimador.fit(treino)
        previsto = np.asarray(estimador.prever(teste.size), dtype=float)
        y_real.extend(teste.tolist())
        y_prev.extend(previsto.tolist())

    resultado = metrics.calcular_todas(y_real, y_prev)
    resultado["n_dobras"] = n_dobras
    return resultado


def comparar_algoritmos(
    serie,
    algoritmos=ALGORITMOS,
    *,
    n_dobras: int = 3,
    horizonte: int = 1,
    fabrica: Callable[[str], Estimador] | None = None,
) -> list[ResultadoAvaliacao]:
    """Avalia cada algoritmo por walk-forward. ``fabrica`` permite injetar um
    estimador alternativo (ex.: um estimador falso nos testes de orquestração)."""
    construir = fabrica or criar
    resultados: list[ResultadoAvaliacao] = []
    for algoritmo in algoritmos:
        metricas = walk_forward(
            serie,
            lambda a=algoritmo: construir(a),
            n_dobras=n_dobras,
            horizonte=horizonte,
        )
        resultados.append(
            ResultadoAvaliacao(
                algoritmo=algoritmo,
                mae=metricas["mae"],
                rmse=metricas["rmse"],
                mape=metricas["mape"],
            )
        )
    return resultados


def selecionar_melhor(
    resultados: list[ResultadoAvaliacao], *, criterio: str = "mape"
) -> ResultadoAvaliacao:
    """Menor valor da métrica escolhida (RFC 5.6.4). Resultados com métrica ``nan``
    só são escolhidos se não houver nenhum válido."""
    if not resultados:
        raise ValueError("Não há resultados para selecionar.")

    def chave(resultado: ResultadoAvaliacao) -> float:
        valor = getattr(resultado, criterio)
        return float("inf") if math.isnan(valor) else valor

    return min(resultados, key=chave)
