"""Testes da fábrica de estimadores."""

import math

import numpy as np
import pytest
from dateutil.relativedelta import relativedelta

from app.services.ml import estimadores as est


def test_criar_retorna_estimador_para_cada_algoritmo():
    for algoritmo in est.ALGORITMOS:
        estimador = est.criar(algoritmo)
        assert hasattr(estimador, "fit")
        assert hasattr(estimador, "prever")


def test_criar_algoritmo_desconhecido_levanta():
    with pytest.raises(ValueError):
        est.criar("profeta_misterioso")


def test_sma_preve_media_da_janela():
    estimador = est.criar_sma(janela=3).fit([10, 20, 30])
    previsao = estimador.prever(2)
    assert list(previsao) == [20.0, 20.0]


def test_arvore_serie_curta_cai_para_media():
    # Série menor que n_lags: não treina LightGBM, prevê a média.
    estimador = est.criar_gradient_boosting().fit([5, 7])
    previsao = estimador.prever(1)
    assert previsao[0] == pytest.approx(6.0)


def _serie_24_meses() -> np.ndarray:
    return np.array([100 + 5 * i + (20 if (i % 12) in (10, 11) else 0) for i in range(24)], dtype=float)


@pytest.mark.lento
@pytest.mark.parametrize("algoritmo", est.ALGORITMOS)
def test_todos_estimadores_treinam_e_preveem(algoritmo):
    estimador = est.criar(algoritmo).fit(_serie_24_meses())
    previsao = estimador.prever(6)
    assert len(previsao) == 6
    assert all(math.isfinite(v) for v in previsao)
