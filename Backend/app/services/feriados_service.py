import logging
import unicodedata
from datetime import date, datetime

import httpx
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.feriados import Feriado
from app.models.feriado_sincronizacao import FeriadoSincronizacao

logger = logging.getLogger(__name__)

# Mapeia os valores de tipo/nível retornados pela API para o vocabulário interno.
_MAPA_TIPO = {
    "national": "nacional",
    "nacional": "nacional",
    "state": "estadual",
    "estadual": "estadual",
    "regional": "estadual",
    "municipal": "municipal",
    "city": "municipal",
    "local": "municipal",
}


def _normalizar_localidade(texto: str) -> str:
    """Remove acentos e formata como o código de localidade da API (ex: 'São Paulo' -> 'SAO-PAULO')."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.strip().upper().replace(" ", "-")


def _classificar_tipo(item: dict) -> str:
    bruto = str(item.get("type") or item.get("level") or item.get("tipo") or "").lower()
    tipo = _MAPA_TIPO.get(bruto)
    if not tipo:
        logger.warning("Tipo de feriado desconhecido retornado pela API: %r — item=%r", bruto, item)
        tipo = bruto or "desconhecido"
    return tipo


def _extrair_lista(payload: dict) -> list[dict]:
    if isinstance(payload, list):
        return payload
    for chave in ("data", "holidays", "results", "items"):
        valor = payload.get(chave)
        if isinstance(valor, list):
            return valor
    logger.warning("Formato de resposta inesperado da API de feriados: %r", payload)
    return []


def _buscar_feriados_api(uf: str, cidade: str, ano: int) -> list[dict]:
    localidade = f"{uf.upper()}-{_normalizar_localidade(cidade)}"
    url = f"{settings.FERIADOSAPI_BASE_URL}/v1/holidays"
    params = {"location": localidade, "year": ano, "limit": 100}
    headers = {"X-API-Key": settings.FERIADOSAPI_KEY}

    resposta = httpx.get(url, params=params, headers=headers, timeout=15)
    resposta.raise_for_status()
    payload = resposta.json()

    if isinstance(payload, dict) and payload.get("status") == "error":
        raise RuntimeError(f"Erro da API feriados.dev: {payload.get('message')}")

    return _extrair_lista(payload)


def _mapear_item(item: dict, uf: str, cidade: str) -> dict | None:
    data_str = item.get("date") or item.get("data")
    nome = item.get("name") or item.get("nome") or item.get("description")
    if not data_str or not nome:
        logger.warning("Item de feriado sem data ou nome, ignorado: %r", item)
        return None

    try:
        data_feriado = datetime.strptime(str(data_str)[:10], "%Y-%m-%d").date()
    except ValueError:
        logger.warning("Data de feriado em formato inesperado, ignorado: %r", item)
        return None

    tipo = _classificar_tipo(item)
    if tipo == "nacional":
        uf_registro, cidade_registro = None, None
    elif tipo == "estadual":
        uf_registro, cidade_registro = uf, None
    else:
        uf_registro, cidade_registro = uf, cidade

    return {
        "data": data_feriado,
        "uf": uf_registro,
        "cidade": cidade_registro,
        "ds_feriado": str(nome).strip(),
        "tipo": tipo,
    }


def sincronizar_feriados(db: Session, uf: str, cidade: str, ano: int) -> None:
    """Busca os feriados de uf/cidade/ano na feriados.dev e cacheia no banco, se ainda não sincronizado."""
    ja_sincronizado = (
        db.query(FeriadoSincronizacao)
        .filter(
            FeriadoSincronizacao.uf == uf,
            FeriadoSincronizacao.cidade == cidade,
            FeriadoSincronizacao.ano == ano,
        )
        .first()
    )
    if ja_sincronizado:
        return

    logger.info("Sincronizando feriados uf=%s cidade=%s ano=%s", uf, cidade, ano)
    itens_api = _buscar_feriados_api(uf, cidade, ano)
    registros = [
        registro
        for item in itens_api
        if (registro := _mapear_item(item, uf, cidade)) is not None
    ]

    for registro in registros:
        # Comparação manual (não ON CONFLICT) porque uf/cidade nulos (nacional/estadual)
        # não colidem entre si em UNIQUE constraints do Postgres (NULL != NULL).
        existe = (
            db.query(Feriado.id)
            .filter(
                Feriado.data == registro["data"],
                Feriado.uf.is_(None) if registro["uf"] is None else Feriado.uf == registro["uf"],
                Feriado.cidade.is_(None) if registro["cidade"] is None else Feriado.cidade == registro["cidade"],
                Feriado.tipo == registro["tipo"],
                Feriado.ds_feriado == registro["ds_feriado"],
            )
            .first()
        )
        if not existe:
            db.add(Feriado(**registro))

    db.add(FeriadoSincronizacao(uf=uf, cidade=cidade, ano=ano))
    db.commit()
    logger.info("Sincronização concluída uf=%s cidade=%s ano=%s registros=%s", uf, cidade, ano, len(registros))


def obter_feriados(db: Session, uf: str, cidade: str, ano: int) -> list[Feriado]:
    """Retorna os feriados aplicáveis a uf/cidade no ano informado, sincronizando sob demanda."""
    sincronizar_feriados(db, uf, cidade, ano)

    return (
        db.query(Feriado)
        .filter(
            Feriado.data.between(date(ano, 1, 1), date(ano, 12, 31)),
            or_(
                Feriado.uf.is_(None),
                and_(Feriado.uf == uf, Feriado.cidade.is_(None)),
                and_(Feriado.uf == uf, Feriado.cidade == cidade),
            ),
        )
        .order_by(Feriado.data)
        .all()
    )


def esta_de_feriado(db: Session, dia: date, uf: str, cidade: str) -> Feriado | None:
    """Verifica se uma data específica é feriado para a uf/cidade informada."""
    feriados_do_ano = obter_feriados(db, uf, cidade, dia.year)
    for feriado in feriados_do_ano:
        if feriado.data == dia:
            return feriado
    return None
