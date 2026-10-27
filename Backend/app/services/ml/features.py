from datetime import date

import pandas as pd

LAGS = (1, 2, 3, 6, 12)
JANELAS_MOVEIS = (3, 6, 12)
# Meses de maior consumo hospitalar (inverno + fim de ano).
MESES_ALTA_SAZONALIDADE = {5, 6, 7, 11, 12}

# Colunas de atributo que não podem conter NaN na matriz final.
_COLUNAS_LAG_MM = [f"lag_{l}" for l in LAGS] + [f"media_movel_{j}" for j in JANELAS_MOVEIS]


def adicionar_lags(df: pd.DataFrame, coluna: str = "quantidade_total", lags=LAGS) -> pd.DataFrame:
    df = df.copy()
    for lag in lags:
        df[f"lag_{lag}"] = df[coluna].shift(lag)
    return df


def adicionar_medias_moveis(
    df: pd.DataFrame, coluna: str = "quantidade_total", janelas=JANELAS_MOVEIS
) -> pd.DataFrame:
    df = df.copy()
    for janela in janelas:
        # shift(1) garante que a média usa só o passado (sem vazar o alvo atual).
        df[f"media_movel_{janela}"] = df[coluna].shift(1).rolling(janela).mean()
    return df


def adicionar_indicadores_calendario(df: pd.DataFrame, coluna_data: str = "periodo") -> pd.DataFrame:
    df = df.copy()
    periodo = pd.to_datetime(df[coluna_data])
    df["mes"] = periodo.dt.month
    df["trimestre"] = periodo.dt.quarter
    df["fim_de_ano"] = periodo.dt.month.isin([11, 12]).astype(int)
    df["mes_alta_sazonalidade"] = periodo.dt.month.isin(MESES_ALTA_SAZONALIDADE).astype(int)
    return df


def adicionar_flag_feriado(
    df: pd.DataFrame, feriados: list[date], coluna_data: str = "periodo"
) -> pd.DataFrame:
    df = df.copy()
    meses_feriado: dict[tuple[int, int], int] = {}
    for feriado in feriados:
        chave = (feriado.year, feriado.month)
        meses_feriado[chave] = meses_feriado.get(chave, 0) + 1

    periodo = pd.to_datetime(df[coluna_data])
    df["qtd_feriados_no_mes"] = [
        meses_feriado.get((p.year, p.month), 0) for p in periodo
    ]
    df["tem_feriado"] = (df["qtd_feriados_no_mes"] > 0).astype(int)
    return df


def adicionar_categoricas(
    df: pd.DataFrame, classe_abc: str | None, local_estoque: str | None
) -> pd.DataFrame:
    df = df.copy()
    df["classe_abc"] = classe_abc or "SEM_CLASSE"
    df["local_estoque"] = local_estoque or "DESCONHECIDO"
    return df

#dropna(subset=_COLUNAS_LAG_MM) descarta todas as linhas para séries menores que 13 meses; módulo desacoplado do pipeline.
def construir_matriz(
    df: pd.DataFrame,
    feriados: list[date],
    classe_abc: str | None,
    local_estoque: str | None,
    coluna: str = "quantidade_total",
    coluna_data: str = "periodo",
) -> pd.DataFrame:
    """Pipeline completo de atributos. Ordena no tempo e remove as linhas iniciais
    que ficam com NaN nos lags/médias móveis, garantindo uma matriz sem buracos."""
    df = df.sort_values(coluna_data).reset_index(drop=True)
    df = adicionar_lags(df, coluna)
    df = adicionar_medias_moveis(df, coluna)
    df = adicionar_indicadores_calendario(df, coluna_data)
    df = adicionar_flag_feriado(df, feriados, coluna_data)
    df = adicionar_categoricas(df, classe_abc, local_estoque)
    df = df.dropna(subset=_COLUNAS_LAG_MM).reset_index(drop=True)
    return df
