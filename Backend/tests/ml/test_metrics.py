"""Testes das métricas de avaliação (funções puras)."""

import math

import numpy as np
import pytest

from app.services.ml import metrics


def test_mae_valores_conhecidos():
    assert metrics.mae([10, 20, 30], [12, 18, 33]) == pytest.approx((2 + 2 + 3) / 3)


def test_rmse_valores_conhecidos():
    # erros [0, 4] -> sqrt(mean([0, 16])) = sqrt(8)
    assert metrics.rmse([10, 20], [10, 24]) == pytest.approx(math.sqrt(8))


def test_rmse_penaliza_erro_grande_mais_que_mae():
    y_real = [10, 10, 10, 10]
    y_prev = [10, 10, 10, 30]  # um erro grande isolado
    assert metrics.rmse(y_real, y_prev) > metrics.mae(y_real, y_prev)


def test_mape_valores_conhecidos():
    # |(100-90)/100| = 0.1 -> 10%
    assert metrics.mape([100], [90]) == pytest.approx(10.0)


def test_mape_ignora_posicoes_com_real_zero():
    # a posição com real 0 é ignorada; sobra |(100-80)/100| = 20%
    assert metrics.mape([0, 100], [50, 80]) == pytest.approx(20.0)


def test_mape_todos_zeros_retorna_nan():
    assert math.isnan(metrics.mape([0, 0], [5, 9]))


def test_mape_previsao_perfeita_retorna_zero():
    assert metrics.mape([10, 20, 30], [10, 20, 30]) == pytest.approx(0.0)


def test_calcular_todas_retorna_tres_chaves():
    resultado = metrics.calcular_todas([10, 20], [11, 19])
    assert set(resultado) == {"mae", "rmse", "mape"}


def test_metricas_com_array_vazio():
    assert math.isnan(metrics.mae([], []))
    assert math.isnan(metrics.rmse([], []))
    assert math.isnan(metrics.mape([], []))


def test_metricas_rejeitam_tamanhos_diferentes():
    with pytest.raises(ValueError):
        metrics.mae([1, 2, 3], [1, 2])
