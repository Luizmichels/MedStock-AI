"""Camada de consulta de itens, consumos e séries temporais (RF03).

Toda consulta é sempre filtrada por ``empresa_id`` para garantir o isolamento
de dados entre empresas (RF16).
"""

from datetime import date

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.classificacao_abc import ClassificacaoABC
from app.models.consumo import Consumo
from app.models.consumo_tratado import ConsumoTratado
from app.models.itens import Item
from app.schemas.comuns import Pagina
from app.schemas.consumo_schemas import ConsumoResponse, PontoSerie
from app.schemas.item_schemas import ItemResponse


def _normalizar_paginacao(pagina: int, tamanho: int) -> tuple[int, int]:
    pagina = max(pagina, 1)
    tamanho = min(max(tamanho, 1), 200)
    return pagina, tamanho


def listar_itens(
    db: Session,
    empresa_id: int,
    *,
    busca: str | None = None,
    classe_abc: str | None = None,
    pagina: int = 1,
    tamanho: int = 50,
) -> Pagina[ItemResponse]:
    pagina, tamanho = _normalizar_paginacao(pagina, tamanho)

    query = (
        db.query(Item, ClassificacaoABC.classe)
        .outerjoin(
            ClassificacaoABC,
            (ClassificacaoABC.item_id == Item.id)
            & (ClassificacaoABC.empresa_id == empresa_id),
        )
        .filter(Item.empresa_id == empresa_id)
    )

    if busca:
        curinga = f"%{busca}%"
        query = query.filter(
            or_(Item.codigo_item.ilike(curinga), Item.descricao_item.ilike(curinga))
        )
    if classe_abc:
        query = query.filter(ClassificacaoABC.classe == classe_abc)

    total = query.count()
    linhas = (
        query.order_by(Item.codigo_item)
        .offset((pagina - 1) * tamanho)
        .limit(tamanho)
        .all()
    )

    itens: list[ItemResponse] = []
    for item, classe in linhas:
        resposta = ItemResponse.model_validate(item)
        resposta.classe_abc = classe
        itens.append(resposta)

    return Pagina(itens=itens, total=total, pagina=pagina, tamanho=tamanho)


def obter_item(db: Session, empresa_id: int, item_id: int) -> Item | None:
    return (
        db.query(Item)
        .filter(Item.id == item_id, Item.empresa_id == empresa_id)
        .first()
    )


def classe_abc_do_item(db: Session, empresa_id: int, item_id: int) -> str | None:
    classe = (
        db.query(ClassificacaoABC.classe)
        .filter(
            ClassificacaoABC.empresa_id == empresa_id,
            ClassificacaoABC.item_id == item_id,
        )
        .scalar()
    )
    return classe


def listar_consumos(
    db: Session,
    empresa_id: int,
    *,
    item_id: int | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    local: str | None = None,
    pagina: int = 1,
    tamanho: int = 50,
) -> Pagina[ConsumoResponse]:
    pagina, tamanho = _normalizar_paginacao(pagina, tamanho)

    query = db.query(Consumo).filter(Consumo.empresa_id == empresa_id)
    if item_id is not None:
        query = query.filter(Consumo.item_id == item_id)
    if data_inicio is not None:
        query = query.filter(Consumo.data >= data_inicio)
    if data_fim is not None:
        query = query.filter(Consumo.data <= data_fim)
    if local:
        query = query.filter(Consumo.local_estoque == local)

    total = query.count()
    registros = (
        query.order_by(Consumo.data.desc(), Consumo.id.desc())
        .offset((pagina - 1) * tamanho)
        .limit(tamanho)
        .all()
    )
    itens = [ConsumoResponse.model_validate(c) for c in registros]

    return Pagina(itens=itens, total=total, pagina=pagina, tamanho=tamanho)


def obter_serie_temporal(db: Session, empresa_id: int, item_id: int) -> list[PontoSerie]:
    linhas = (
        db.query(
            ConsumoTratado.periodo,
            func.sum(ConsumoTratado.quantidade_total),
            func.sum(ConsumoTratado.valor_total),
        )
        .filter(
            ConsumoTratado.empresa_id == empresa_id,
            ConsumoTratado.item_id == item_id,
        )
        .group_by(ConsumoTratado.periodo)
        .order_by(ConsumoTratado.periodo)
        .all()
    )
    return [
        PontoSerie(periodo=periodo, quantidade_total=float(qtd), valor_total=float(valor))
        for periodo, qtd, valor in linhas
    ]


def contar_meses_de_historico(db: Session, empresa_id: int, item_id: int) -> int:
    """Número de meses distintos com consumo tratado — base da RN06 (elegibilidade)."""
    total = (
        db.query(func.count(func.distinct(ConsumoTratado.periodo)))
        .filter(
            ConsumoTratado.empresa_id == empresa_id,
            ConsumoTratado.item_id == item_id,
        )
        .scalar()
    )
    return int(total or 0)
