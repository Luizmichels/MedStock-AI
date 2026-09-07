"""Testes da elegibilidade de itens (RN06 / FA03)."""

import pandas as pd

from app.services.ml import elegibilidade as el


def _serie(n: int) -> pd.DataFrame:
    return pd.DataFrame({"quantidade_total": list(range(n))})


def test_item_elegivel_com_historico_suficiente():
    assert el.item_elegivel(_serie(6)) is True


def test_item_inelegivel_com_historico_curto():
    assert el.item_elegivel(_serie(2)) is False


def test_item_elegivel_no_limite_exato():
    assert el.item_elegivel(_serie(el.MESES_MINIMOS)) is True


def test_separar_elegiveis_divide_corretamente():
    series = {1: _serie(6), 2: _serie(1)}
    elegiveis, omitidos = el.separar_elegiveis(series)
    assert set(elegiveis) == {1}
    assert [o.item_id for o in omitidos] == [2]


def test_separar_elegiveis_registra_motivo_do_omitido():
    _, omitidos = el.separar_elegiveis({9: _serie(1)})
    assert "insuficiente" in omitidos[0].motivo.lower()


def test_separar_elegiveis_conta_meses_disponiveis():
    _, omitidos = el.separar_elegiveis({9: _serie(2)})
    assert omitidos[0].meses_disponiveis == 2
