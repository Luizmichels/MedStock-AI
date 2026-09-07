"""Testes da validação walk-forward e seleção do melhor algoritmo."""

import math

import pytest

from app.services.ml import validacao as vd
from app.services.ml.estimadores import ALGORITMOS
from app.services.ml.validacao import ResultadoAvaliacao
from tests.ml.fakes import EstimadorFake, fabrica_fake

SERIE = [10, 12, 11, 13, 12, 14, 13, 15, 14, 16, 15, 17]


def test_walk_forward_retorna_metricas():
    resultado = vd.walk_forward(SERIE, EstimadorFake, n_dobras=3, horizonte=1)
    assert {"mae", "rmse", "mape", "n_dobras"} <= set(resultado)
    assert resultado["mae"] >= 0


def test_walk_forward_numero_de_dobras():
    resultado = vd.walk_forward(SERIE, EstimadorFake, n_dobras=3, horizonte=1)
    assert resultado["n_dobras"] == 3


def test_walk_forward_serie_curta_reduz_dobras():
    resultado = vd.walk_forward([10, 20], EstimadorFake, n_dobras=3, horizonte=1)
    assert resultado["n_dobras"] == 1


def test_walk_forward_horizonte_maior_que_um():
    resultado = vd.walk_forward(SERIE, EstimadorFake, n_dobras=2, horizonte=3)
    assert not math.isnan(resultado["mae"])


def test_comparar_algoritmos_retorna_um_por_algoritmo():
    resultados = vd.comparar_algoritmos(
        SERIE, algoritmos=("x", "y", "z"), fabrica=fabrica_fake
    )
    assert len(resultados) == 3


def test_comparar_algoritmos_usa_todos_os_cinco_por_padrao():
    resultados = vd.comparar_algoritmos(SERIE, fabrica=fabrica_fake)
    assert [r.algoritmo for r in resultados] == list(ALGORITMOS)


def test_selecionar_melhor_menor_mape():
    resultados = [
        ResultadoAvaliacao("a", mae=1, rmse=1, mape=30.0),
        ResultadoAvaliacao("b", mae=1, rmse=1, mape=10.0),
        ResultadoAvaliacao("c", mae=1, rmse=1, mape=20.0),
    ]
    assert vd.selecionar_melhor(resultados).algoritmo == "b"


def test_selecionar_melhor_ignora_nan():
    resultados = [
        ResultadoAvaliacao("a", mae=1, rmse=1, mape=float("nan")),
        ResultadoAvaliacao("b", mae=1, rmse=1, mape=25.0),
    ]
    assert vd.selecionar_melhor(resultados).algoritmo == "b"


def test_selecionar_melhor_lista_vazia_levanta():
    with pytest.raises(ValueError):
        vd.selecionar_melhor([])
