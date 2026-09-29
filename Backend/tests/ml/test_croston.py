"""Testes do método de Croston/SBA."""

from app.services.ml.croston import croston


def test_croston_sem_demanda_retorna_zero():
    assert croston([0, 0, 0, 0]) == 0.0


def test_croston_demanda_constante_taxa_igual_ao_nivel():
    # Demanda 10 todo dia -> intervalo 1 -> taxa ~= 10.
    taxa = croston([10] * 20, variante="classico")
    assert abs(taxa - 10.0) < 0.5


def test_croston_intermitente_taxa_aproxima_media_diaria():
    # Demanda 5 a cada 5 dias -> taxa diária ~= 1.0.
    serie = ([5] + [0, 0, 0, 0]) * 8
    taxa = croston(serie, variante="classico")
    assert 0.7 < taxa < 1.3


def test_sba_corrige_vies_para_baixo():
    serie = ([5] + [0, 0, 0, 0]) * 8
    classico = croston(serie, variante="classico")
    sba = croston(serie, variante="sba")
    assert sba < classico
