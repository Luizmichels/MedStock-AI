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


def test_walk_forward_devolve_o_previsto_de_cada_mes_de_teste():
    # 12 meses, 3 dobras de 3: os 9 últimos (posições 3 a 11) são previstos.
    resultado = vd.walk_forward(SERIE, EstimadorFake, n_dobras=3, horizonte=3)
    assert [indice for indice, _ in resultado["previstos"]] == list(range(3, 12))
    # O fake prevê a média do treino: a 1ª dobra treina com [10, 12, 11].
    assert resultado["previstos"][0][1] == pytest.approx(11.0)


def test_comparar_algoritmos_guarda_os_previstos():
    resultados = vd.comparar_algoritmos(SERIE, algoritmos=("x",), fabrica=fabrica_fake, horizonte=3)
    assert len(resultados[0].previstos) == 9


def test_walk_forward_serie_curta_reduz_horizonte_para_caber():
    # 3 meses com horizonte 3: sobra 1 mês de treino e o horizonte cai para 2.
    resultado = vd.walk_forward([10, 20, 30], EstimadorFake, n_dobras=3, horizonte=3)
    assert resultado["n_dobras"] == 1
    assert resultado["mae"] == 15.0  # treina com [10] e prevê 10, 10 para [20, 30]
    assert resultado["previstos"] == [(1, 10.0), (2, 10.0)]
