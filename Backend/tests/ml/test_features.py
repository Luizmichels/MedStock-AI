"""Testes da engenharia de atributos (funções puras)."""

from datetime import date

import pandas as pd
from dateutil.relativedelta import relativedelta

from app.services.ml import features as ft


def _serie(n: int = 18, inicio: date = date(2024, 1, 1)) -> pd.DataFrame:
    periodos = [inicio + relativedelta(months=i) for i in range(n)]
    return pd.DataFrame(
        {"periodo": periodos, "quantidade_total": [float(10 * (i + 1)) for i in range(n)]}
    )


def test_adicionar_lags_cria_cinco_colunas():
    df = ft.adicionar_lags(_serie())
    for lag in ft.LAGS:
        assert f"lag_{lag}" in df.columns


def test_lag_1_reproduz_valor_do_mes_anterior():
    df = ft.adicionar_lags(_serie())
    assert df.loc[1, "lag_1"] == df.loc[0, "quantidade_total"]


def test_lags_iniciais_ficam_nulos():
    df = ft.adicionar_lags(_serie())
    assert pd.isna(df.loc[0, "lag_1"])


def test_medias_moveis_tres_janelas():
    df = ft.adicionar_medias_moveis(_serie())
    for janela in ft.JANELAS_MOVEIS:
        assert f"media_movel_{janela}" in df.columns


def test_media_movel_3_confere_com_calculo_manual():
    df = ft.adicionar_medias_moveis(_serie())
    # shift(1) + rolling(3): no índice 3 é a média de 10, 20, 30.
    assert df.loc[3, "media_movel_3"] == (10 + 20 + 30) / 3


def test_indicadores_calendario_mes_e_trimestre():
    df = ft.adicionar_indicadores_calendario(_serie())
    assert df.loc[0, "mes"] == 1
    assert df.loc[0, "trimestre"] == 1


def test_indicador_fim_de_ano_marca_novembro_e_dezembro():
    df = ft.adicionar_indicadores_calendario(_serie())
    # inicio jan/2024: nov=índice 10, dez=índice 11.
    assert df.loc[10, "fim_de_ano"] == 1
    assert df.loc[11, "fim_de_ano"] == 1
    assert df.loc[0, "fim_de_ano"] == 0


def test_flag_feriado_conta_feriados_do_mes():
    df = ft.adicionar_flag_feriado(
        _serie(), [date(2024, 1, 1), date(2024, 1, 20)]
    )
    assert df.loc[0, "qtd_feriados_no_mes"] == 2
    assert df.loc[0, "tem_feriado"] == 1


def test_flag_feriado_sem_feriados_fica_zero():
    df = ft.adicionar_flag_feriado(_serie(), [])
    assert df["qtd_feriados_no_mes"].sum() == 0
    assert df["tem_feriado"].sum() == 0


def test_categoricas_recebem_classe_abc():
    df = ft.adicionar_categoricas(_serie(), "A", "Central")
    assert (df["classe_abc"] == "A").all()


def test_categoricas_com_local_nulo():
    df = ft.adicionar_categoricas(_serie(), "B", None)
    assert (df["local_estoque"] == "DESCONHECIDO").all()


def test_construir_matriz_nao_deixa_nan_nas_features_finais():
    matriz = ft.construir_matriz(_serie(), [], "A", "Central")
    assert not matriz[ft._COLUNAS_LAG_MM].isna().any().any()
    assert len(matriz) > 0


def test_construir_matriz_preserva_ordem_temporal():
    embaralhada = _serie().sample(frac=1, random_state=1)
    matriz = ft.construir_matriz(embaralhada, [], "A", "Central")
    periodos = list(matriz["periodo"])
    assert periodos == sorted(periodos)


def test_construir_matriz_serie_curta_nao_quebra():
    matriz = ft.construir_matriz(_serie(n=2), [], "A", "Central")
    assert len(matriz) == 0
