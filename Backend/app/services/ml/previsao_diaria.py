"""Pipeline de previsão em granularidade DIÁRIA.

Fluxo por item:
1. Monta a série diária a partir de ``consumos`` (dia sem consumo = 0), num
   calendário comum que termina na última data da empresa (origem única).
2. Classifica a intermitência (SBC) e escolhe o método:
   - intermitente/lumpy  -> Croston/SBA (taxa diária constante);
   - suave/erratico      -> média móvel recente × perfil de dia da semana.
3. Prevê ``HORIZONTE_DIARIO`` dias à frente e persiste os pontos diários.

Os horizontes de 7, 15 e 30 dias (e o mensal) são somas destes pontos, feitas na
leitura — ver ``resumo_por_item``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.consumo import Consumo
from app.models.previsao_diaria import PrevisaoDiaria
from app.services.ml.croston import croston
from app.services.ml.intermitencia import calcular_metricas, classificar_sbc

HORIZONTE_DIARIO = 30
# Histórico próprio mínimo (em dias) para um item ser previsto no diário.
DIAS_MINIMOS = 28
# Janela da média móvel para itens regulares.
JANELA_MEDIA = 28
# Limites do fator de dia da semana, para o perfil não explodir com pouca amostra.
_FATOR_MIN, _FATOR_MAX = 0.3, 3.0


@dataclass
class SerieDiaria:
    item_id: int
    valores: np.ndarray      # série diária contínua [inicio_item .. referencia]
    inicio: date             # primeiro dia observado do item
    fim_observado: date      # último dia observado do item
    referencia: date         # origem comum (última data da empresa)


def carregar_series_diarias(db: Session, empresa_id: int) -> list[SerieDiaria]:
    """Séries diárias por item, no calendário comum [inicio_item .. referencia]."""
    linhas = (
        db.query(Consumo.item_id, Consumo.data, func.sum(Consumo.quantidade))
        .filter(Consumo.empresa_id == empresa_id)
        .group_by(Consumo.item_id, Consumo.data)
        .all()
    )
    por_item: dict[int, dict[date, float]] = {}
    datas_globais: list[date] = []
    for item_id, dia, qtd in linhas:
        por_item.setdefault(item_id, {})[dia] = float(qtd)
        datas_globais.append(dia)

    if not datas_globais:
        return []
    referencia = max(datas_globais)

    series: list[SerieDiaria] = []
    for item_id, por_dia in por_item.items():
        inicio = min(por_dia)
        fim_obs = max(por_dia)
        n = (referencia - inicio).days + 1
        valores = np.zeros(n, dtype=float)
        for dia, qtd in por_dia.items():
            valores[(dia - inicio).days] = qtd
        series.append(SerieDiaria(item_id, valores, inicio, fim_obs, referencia))
    return series


def _perfil_dia_semana(valores: np.ndarray, inicio: date, fim_obs: date) -> np.ndarray:
    """Fatores multiplicativos por dia da semana (seg=0..dom=6), sobre o período
    observado do item (ignora o padding após o último consumo)."""
    n_obs = (fim_obs - inicio).days + 1
    observado = valores[:n_obs]
    media_geral = observado.mean()
    fatores = np.ones(7, dtype=float)
    if media_geral <= 0:
        return fatores
    for w in range(7):
        # posições cujo dia da semana é w
        idx = [i for i in range(n_obs) if (inicio + timedelta(days=i)).weekday() == w]
        if idx:
            fator = float(observado[idx].mean() / media_geral)
            fatores[w] = min(max(fator, _FATOR_MIN), _FATOR_MAX)
    return fatores


def prever_item(serie: SerieDiaria) -> tuple[list[float], str]:
    """Vetor de ``HORIZONTE_DIARIO`` previsões diárias e o método usado."""
    valores = serie.valores
    adi, cv2, _ = calcular_metricas(valores)
    classe = classificar_sbc(adi, cv2) if adi is not None and cv2 is not None else "sem_dados"

    if classe in ("intermitente", "lumpy") or adi is None:
        taxa = croston(valores, variante="sba")
        return [taxa] * HORIZONTE_DIARIO, "croston_sba"

    # Itens regulares: média móvel recente × perfil de dia da semana.
    base = float(valores[-JANELA_MEDIA:].mean()) if valores.size else 0.0
    fatores = _perfil_dia_semana(valores, serie.inicio, serie.fim_observado)
    previsoes: list[float] = []
    for passo in range(1, HORIZONTE_DIARIO + 1):
        dia = serie.referencia + timedelta(days=passo)
        previsoes.append(max(base * fatores[dia.weekday()], 0.0))
    return previsoes, "media_movel_sazonal"


def gerar_previsoes_diarias(db: Session, empresa_id: int) -> int:
    """Gera e persiste as previsões diárias da empresa. Retorna o nº de itens
    previstos. Regenera do zero (descarta as previsões diárias anteriores)."""
    series = carregar_series_diarias(db, empresa_id)

    db.query(PrevisaoDiaria).filter(PrevisaoDiaria.empresa_id == empresa_id).delete()

    itens_previstos = 0
    for serie in series:
        span = (serie.fim_observado - serie.inicio).days + 1
        if span < DIAS_MINIMOS:
            continue  # histórico próprio insuficiente (equivalente ao RN06 diário)

        previsoes, metodo = prever_item(serie)
        registros = [
            {
                "empresa_id": empresa_id,
                "item_id": serie.item_id,
                "data": serie.referencia + timedelta(days=passo),
                "quantidade_prevista": float(valor),
                "metodo": metodo,
            }
            for passo, valor in enumerate(previsoes, start=1)
        ]
        db.bulk_insert_mappings(PrevisaoDiaria, registros)
        itens_previstos += 1

    db.commit()
    return itens_previstos


def resumo_por_item(db: Session, empresa_id: int, item_id: int | None = None) -> list[dict]:
    """Para cada item, soma os pontos diários nos horizontes 7/15/30 dias e o
    próximo dia. As somas partem sempre do 1º dia previsto."""
    query = db.query(PrevisaoDiaria).filter(PrevisaoDiaria.empresa_id == empresa_id)
    if item_id is not None:
        query = query.filter(PrevisaoDiaria.item_id == item_id)
    pontos = query.order_by(PrevisaoDiaria.item_id, PrevisaoDiaria.data).all()

    por_item: dict[int, list[PrevisaoDiaria]] = {}
    for p in pontos:
        por_item.setdefault(p.item_id, []).append(p)

    resultado: list[dict] = []
    for iid, lista in por_item.items():
        valores = [p.quantidade_prevista for p in lista]
        resultado.append({
            "item_id": iid,
            "metodo": lista[0].metodo,
            "base": lista[0].data - timedelta(days=1),  # referência (dia anterior ao 1º previsto)
            "proximo_dia": round(valores[0], 3) if valores else 0.0,
            "sete_dias": round(sum(valores[:7]), 3),
            "quinze_dias": round(sum(valores[:15]), 3),
            "trinta_dias": round(sum(valores[:30]), 3),
        })
    return resultado
