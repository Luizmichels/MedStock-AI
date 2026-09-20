"""Fábrica dos 5 estimadores de previsão (RFC 5.6).

Todos expõem a mesma interface mínima — ``fit(serie)`` e ``prever(horizonte)`` —
para que a validação walk-forward e o treinamento tratem qualquer algoritmo de
forma uniforme. ``serie`` é o vetor mensal de ``quantidade_total`` em ordem
cronológica; ``prever`` devolve ``horizonte`` valores futuros.
"""

from __future__ import annotations

import numpy as np

ALGORITMOS = ("sma", "sarima", "holt_winters", "random_forest", "gradient_boosting")


class Estimador:
    def fit(self, serie) -> "Estimador":  # pragma: no cover - contrato
        raise NotImplementedError

    def prever(self, horizonte: int) -> np.ndarray:  # pragma: no cover - contrato
        raise NotImplementedError


class _EstimadorSMA(Estimador):
    def __init__(self, janela: int = 3):
        self.janela = janela
        self.media = 0.0

    def fit(self, serie) -> "_EstimadorSMA":
        valores = np.asarray(serie, dtype=float)
        if valores.size == 0:
            self.media = 0.0
        else:
            janela = min(self.janela, valores.size)
            self.media = float(np.mean(valores[-janela:]))
        return self

    def prever(self, horizonte: int) -> np.ndarray:
        return np.full(horizonte, self.media)


class _EstimadorHoltWinters(Estimador):
    def __init__(self, sazonalidade: int = 12):
        self.sazonalidade = sazonalidade
        self.resultado = None
        self.fallback = 0.0

    def fit(self, serie) -> "_EstimadorHoltWinters":
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        valores = np.asarray(serie, dtype=float)
        self.fallback = float(np.mean(valores)) if valores.size else 0.0
        try:
            if valores.size >= 2 * self.sazonalidade:
                modelo = ExponentialSmoothing(
                    valores, trend="add", seasonal="add",
                    seasonal_periods=self.sazonalidade,
                )
            else:
                modelo = ExponentialSmoothing(valores, trend="add", seasonal=None)
            self.resultado = modelo.fit()
        except Exception:  # pragma: no cover - fallback de infraestrutura numérica
            self.resultado = None
        return self

    def prever(self, horizonte: int) -> np.ndarray:
        if self.resultado is None:
            return np.full(horizonte, self.fallback)
        return np.asarray(self.resultado.forecast(horizonte), dtype=float)


class _EstimadorSARIMA(Estimador):
    def __init__(self, ordem=(1, 1, 1), ordem_sazonal=(0, 0, 0, 0)):
        self.ordem = ordem
        self.ordem_sazonal = ordem_sazonal
        self.resultado = None
        self.fallback = 0.0

    def fit(self, serie) -> "_EstimadorSARIMA":
        from statsmodels.tsa.statespace.sarimax import SARIMAX

        valores = np.asarray(serie, dtype=float)
        self.fallback = float(np.mean(valores)) if valores.size else 0.0
        try:
            self.resultado = SARIMAX(
                valores,
                order=self.ordem,
                seasonal_order=self.ordem_sazonal,
                enforce_stationarity=False,
                enforce_invertibility=False,
            ).fit(disp=False)
        except Exception:  # pragma: no cover - fallback de infraestrutura numérica
            self.resultado = None
        return self

    def prever(self, horizonte: int) -> np.ndarray:
        if self.resultado is None:
            return np.full(horizonte, self.fallback)
        return np.asarray(self.resultado.forecast(horizonte), dtype=float)


class _EstimadorArvore(Estimador):
    """RandomForest/GradientBoosting via LightGBM sobre atributos de defasagem,
    com previsão multi-step recursiva."""

    def __init__(self, boosting_type: str, n_lags: int = 3, **params):
        self.boosting_type = boosting_type
        self.n_lags = n_lags
        self.params = params
        self.model = None
        self.historico: list[float] = []

    #Falha numérica no LightGBM para séries curtas (3 meses gera len(X) == 0; 4 meses quebra o bagging com 1 amostra).
    @staticmethod
    def _montar_xy(valores: np.ndarray, n_lags: int):
        X, y = [], []
        for i in range(n_lags, len(valores)):
            X.append(valores[i - n_lags:i][::-1])  # [lag_1, lag_2, ...]
            y.append(valores[i])
        return np.array(X), np.array(y)

    def fit(self, serie) -> "_EstimadorArvore":
        from lightgbm import LGBMRegressor

        valores = np.asarray(serie, dtype=float)
        self.historico = list(valores)
        X, y = self._montar_xy(valores, self.n_lags)
        if len(X) == 0:
            self.model = None  # série curta demais: cairá para a média em prever()
            return self
        self.model = LGBMRegressor(boosting_type=self.boosting_type, **self.params)
        self.model.fit(X, y)
        return self

    def prever(self, horizonte: int) -> np.ndarray:
        historico = list(self.historico)
        previsoes = []
        for _ in range(horizonte):
            if self.model is None or len(historico) < self.n_lags:
                prox = float(np.mean(historico)) if historico else 0.0
            else:
                x = np.array(historico[-self.n_lags:][::-1]).reshape(1, -1)
                prox = float(self.model.predict(x)[0])
            previsoes.append(prox)
            historico.append(prox)
        return np.array(previsoes)


_PARAMS_RF = dict(
    n_estimators=50, min_child_samples=1, bagging_fraction=0.8,
    bagging_freq=1, verbose=-1,
)
_PARAMS_GBDT = dict(n_estimators=50, min_child_samples=1, verbose=-1)


def criar_sma(janela: int = 3) -> _EstimadorSMA:
    return _EstimadorSMA(janela)


def criar_sarima(ordem=(1, 1, 1), ordem_sazonal=(0, 0, 0, 0)) -> _EstimadorSARIMA:
    return _EstimadorSARIMA(ordem, ordem_sazonal)


def criar_holt_winters(sazonalidade: int = 12) -> _EstimadorHoltWinters:
    return _EstimadorHoltWinters(sazonalidade)


def criar_random_forest(**params) -> _EstimadorArvore:
    return _EstimadorArvore("rf", **{**_PARAMS_RF, **params})


def criar_gradient_boosting(**params) -> _EstimadorArvore:
    return _EstimadorArvore("gbdt", **{**_PARAMS_GBDT, **params})


_FABRICAS = {
    "sma": criar_sma,
    "sarima": criar_sarima,
    "holt_winters": criar_holt_winters,
    "random_forest": criar_random_forest,
    "gradient_boosting": criar_gradient_boosting,
}


def criar(algoritmo: str, **params) -> Estimador:
    if algoritmo not in _FABRICAS:
        raise ValueError(f"Algoritmo desconhecido: {algoritmo!r}. Use um de {ALGORITMOS}.")
    return _FABRICAS[algoritmo](**params)
