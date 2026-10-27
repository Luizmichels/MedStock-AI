from datetime import date

from dateutil.relativedelta import relativedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.classificacao_abc import ClassificacaoABC
from app.models.consumo_tratado import ConsumoTratado
from app.models.importacoes import Importacao
from app.models.itens import Item
from app.schemas.dashboard_schemas import (
    ConsumoLocal,
    DistribuicaoABC,
    ItemRanking,
    KpisResponse,
    PontoMensal,
)
from app.services.ml.elegibilidade import separar_elegiveis
from app.services.ml.treinamento import carregar_series_por_item


def possui_dados(db: Session, empresa_id: int) -> bool:
    return (
        db.query(ConsumoTratado.id)
        .filter(ConsumoTratado.empresa_id == empresa_id)
        .first()
        is not None
    )


def _cobertura_previsao(db: Session, empresa_id: int) -> float:
    series = carregar_series_por_item(db, empresa_id)
    if not series:
        return 0.0
    elegiveis, _ = separar_elegiveis(series)
    return round(len(elegiveis) / len(series) * 100, 1)


def calcular_kpis(db: Session, empresa_id: int) -> KpisResponse:
    total_itens_ativos = (
        db.query(func.count(Item.id))
        .filter(Item.empresa_id == empresa_id, Item.ativo.is_(True))
        .scalar()
    )
    valor_total = (
        db.query(func.coalesce(func.sum(ConsumoTratado.valor_total), 0.0))
        .filter(ConsumoTratado.empresa_id == empresa_id)
        .scalar()
    )
    numero_importacoes = (
        db.query(func.count(Importacao.id))
        .filter(Importacao.empresa_id == empresa_id)
        .scalar()
    )
    itens_classe_a = (
        db.query(func.count(ClassificacaoABC.id))
        .filter(ClassificacaoABC.empresa_id == empresa_id, ClassificacaoABC.classe == "A")
        .scalar()
    )
    return KpisResponse(
        total_itens_ativos=int(total_itens_ativos or 0),
        valor_total_consumido=float(valor_total or 0.0),
        numero_importacoes=int(numero_importacoes or 0),
        itens_classe_a=int(itens_classe_a or 0),
        cobertura_previsao=_cobertura_previsao(db, empresa_id),
    )


def ultima_importacao(db: Session, empresa_id: int):
    importacao = (
        db.query(Importacao)
        .filter(Importacao.empresa_id == empresa_id)
        .order_by(Importacao.criado_em.desc())
        .first()
    )
    return importacao.criado_em if importacao else None


def consumo_mensal(db: Session, empresa_id: int, *, meses: int = 12) -> list[PontoMensal]:
    linhas = (
        db.query(
            ConsumoTratado.periodo,
            func.sum(ConsumoTratado.quantidade_total),
            func.sum(ConsumoTratado.valor_total),
        )
        .filter(ConsumoTratado.empresa_id == empresa_id)
        .group_by(ConsumoTratado.periodo)
        .order_by(ConsumoTratado.periodo)
        .all()
    )
    if not linhas:
        return []

    por_periodo = {p: (float(q), float(v)) for p, q, v in linhas}
    fim = max(por_periodo)
    inicio = fim - relativedelta(months=meses - 1)

    pontos: list[PontoMensal] = []
    atual = inicio
    while atual <= fim:
        quantidade, valor = por_periodo.get(atual, (0.0, 0.0))
        pontos.append(PontoMensal(periodo=atual, quantidade_total=quantidade, valor_total=valor))
        atual += relativedelta(months=1)
    return pontos


def consumo_por_local(db: Session, empresa_id: int) -> list[ConsumoLocal]:
    linhas = (
        db.query(
            ConsumoTratado.local_estoque,
            func.sum(ConsumoTratado.quantidade_total),
            func.sum(ConsumoTratado.valor_total),
        )
        .filter(ConsumoTratado.empresa_id == empresa_id)
        .group_by(ConsumoTratado.local_estoque)
        .all()
    )
    return [
        ConsumoLocal(local_estoque=local, quantidade_total=float(q), valor_total=float(v))
        for local, q, v in linhas
    ]


#func.count(ClassificacaoABC.item_id) sobre outerjoin multiplica contagem de itens pelos registros de consumo.
def distribuicao_abc(db: Session, empresa_id: int) -> list[DistribuicaoABC]:
    linhas = (
        db.query(
            ClassificacaoABC.classe,
            func.count(ClassificacaoABC.item_id),
            func.coalesce(func.sum(ConsumoTratado.valor_total), 0.0),
        )
        .outerjoin(
            ConsumoTratado,
            (ConsumoTratado.item_id == ClassificacaoABC.item_id)
            & (ConsumoTratado.empresa_id == ClassificacaoABC.empresa_id),
        )
        .filter(ClassificacaoABC.empresa_id == empresa_id)
        .group_by(ClassificacaoABC.classe)
        .order_by(ClassificacaoABC.classe)
        .all()
    )
    return [
        DistribuicaoABC(classe=classe, quantidade_itens=int(qtd), valor_total=float(valor))
        for classe, qtd, valor in linhas
    ]


def top_itens(
    db: Session, empresa_id: int, *, limite: int = 10, por: str = "valor"
) -> list[ItemRanking]:
    coluna = (
        func.sum(ConsumoTratado.valor_total)
        if por == "valor"
        else func.sum(ConsumoTratado.quantidade_total)
    )
    linhas = (
        db.query(
            Item.id,
            Item.codigo_item,
            Item.descricao_item,
            func.sum(ConsumoTratado.quantidade_total),
            func.sum(ConsumoTratado.valor_total),
        )
        .join(ConsumoTratado, ConsumoTratado.item_id == Item.id)
        .filter(ConsumoTratado.empresa_id == empresa_id)
        .group_by(Item.id, Item.codigo_item, Item.descricao_item)
        .order_by(coluna.desc())
        .limit(limite)
        .all()
    )
    return [
        ItemRanking(
            item_id=item_id,
            codigo_item=codigo,
            descricao_item=descricao,
            quantidade_total=float(q),
            valor_total=float(v),
        )
        for item_id, codigo, descricao, q, v in linhas
    ]
