"""Análise de intermitência da demanda — classificação SBC.

Serve para decidir, com dados, se vale a pena prever no DIÁRIO ou se o
horizonte mensal atual já é adequado. Baseia-se em Syntetos-Boylan-Croston (SBC):

- **ADI** = intervalo médio entre demandas (nº de dias ÷ nº de dias com demanda);
- **CV²** = variabilidade do TAMANHO das demandas não-nulas.

Cortes clássicos de Syntetos-Boylan: ADI = 1.32, CV² = 0.49.
A série diária é reconstruída a partir da tabela `consumos` (que guarda a data
de cada lançamento), preenchendo com zero os dias sem consumo.
"""

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.consumo import Consumo

LIMITE_ADI = 1.32
LIMITE_CV2 = 0.49


@dataclass
class Intermitencia:
    item_id: int
    dias_totais: int
    dias_com_demanda: int
    densidade: float
    adi: float | None
    cv2: float | None
    classe: str
    adequado_diario: bool


def classificar_sbc(adi: float, cv2: float) -> str:
    """Classe SBC a partir de ADI e CV² (suave / intermitente / erratico / lumpy)."""
    if adi <= LIMITE_ADI and cv2 <= LIMITE_CV2:
        return "suave"
    if adi > LIMITE_ADI and cv2 <= LIMITE_CV2:
        return "intermitente"
    if adi <= LIMITE_ADI and cv2 > LIMITE_CV2:
        return "erratico"
    return "lumpy"


def calcular_metricas(demandas_diarias) -> tuple[float | None, float | None, int]:
    """(ADI, CV², dias_com_demanda) de uma série DIÁRIA contínua (com zeros)."""
    arr = np.asarray(demandas_diarias, dtype=float)
    nao_nulas = arr[arr > 0]
    n = int(nao_nulas.size)
    if n == 0:
        return None, None, 0
    adi = float(arr.size / n)
    media = float(nao_nulas.mean())
    cv2 = float((nao_nulas.std() / media) ** 2) if media > 0 else None
    return adi, cv2, n


def _serie_diaria(por_dia: dict, inicio: date, fim: date) -> np.ndarray:
    dias = (fim - inicio).days + 1
    return np.array(
        [por_dia.get(inicio + timedelta(days=i), 0.0) for i in range(dias)],
        dtype=float,
    )


def analisar_item(item_id: int, por_dia: dict, inicio: date, fim: date) -> Intermitencia:
    serie = _serie_diaria(por_dia, inicio, fim)
    adi, cv2, n = calcular_metricas(serie)
    if adi is None or cv2 is None:
        classe, adequado = "sem_dados", False
    else:
        classe = classificar_sbc(adi, cv2)
        # Demanda regular (ADI baixo) → previsão diária ponto-a-ponto faz sentido;
        # itens esparsos (intermitente/lumpy) tendem a ficar melhores no mensal.
        adequado = adi <= LIMITE_ADI
    return Intermitencia(
        item_id=item_id,
        dias_totais=int(serie.size),
        dias_com_demanda=n,
        densidade=round(n / serie.size, 3) if serie.size else 0.0,
        adi=round(adi, 3) if adi is not None else None,
        cv2=round(cv2, 3) if cv2 is not None else None,
        classe=classe,
        adequado_diario=adequado,
    )


def analisar_empresa(db: Session, empresa_id: int) -> list[Intermitencia]:
    """Classificação SBC de todos os itens da empresa, a partir do consumo diário."""
    linhas = (
        db.query(Consumo.item_id, Consumo.data, func.sum(Consumo.quantidade))
        .filter(Consumo.empresa_id == empresa_id)
        .group_by(Consumo.item_id, Consumo.data)
        .all()
    )
    por_item: dict[int, dict[date, float]] = {}
    for item_id, dia, qtd in linhas:
        por_item.setdefault(item_id, {})[dia] = float(qtd)

    resultados: list[Intermitencia] = []
    for item_id, por_dia in por_item.items():
        inicio, fim = min(por_dia), max(por_dia)
        resultados.append(analisar_item(item_id, por_dia, inicio, fim))
    return resultados


def resumir(resultados: list[Intermitencia]) -> dict:
    """Contagem por classe SBC e % de itens adequados à previsão diária."""
    total = len(resultados)
    adequados = sum(1 for r in resultados if r.adequado_diario)
    return {
        "total_itens": total,
        "por_classe": dict(Counter(r.classe for r in resultados)),
        "itens_adequados_ao_diario": adequados,
        "percentual_adequado_ao_diario": round(adequados / total * 100, 1) if total else 0.0,
    }
