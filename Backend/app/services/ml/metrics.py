import numpy as np


def _validar(y_real, y_previsto) -> tuple[np.ndarray, np.ndarray]:
    y_real = np.asarray(y_real, dtype=float)
    y_previsto = np.asarray(y_previsto, dtype=float)
    if y_real.shape != y_previsto.shape:
        raise ValueError("y_real e y_previsto devem ter o mesmo tamanho")
    return y_real, y_previsto


def mae(y_real, y_previsto) -> float:
    y_real, y_previsto = _validar(y_real, y_previsto)
    if y_real.size == 0:
        return float("nan")
    return float(np.mean(np.abs(y_real - y_previsto)))


def rmse(y_real, y_previsto) -> float:
    y_real, y_previsto = _validar(y_real, y_previsto)
    if y_real.size == 0:
        return float("nan")
    return float(np.sqrt(np.mean((y_real - y_previsto) ** 2)))


def mape(y_real, y_previsto) -> float:
    """Erro percentual absoluto médio (em %). Ignora posições com y_real == 0."""
    y_real, y_previsto = _validar(y_real, y_previsto)
    mascara = y_real != 0
    if not mascara.any():
        return float("nan")
    erros = np.abs((y_real[mascara] - y_previsto[mascara]) / y_real[mascara])
    return float(np.mean(erros) * 100.0)


def calcular_todas(y_real, y_previsto) -> dict[str, float]:
    return {
        "mae": mae(y_real, y_previsto),
        "rmse": rmse(y_real, y_previsto),
        "mape": mape(y_real, y_previsto),
    }
