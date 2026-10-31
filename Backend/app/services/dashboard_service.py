from dataclasses import dataclass, field
from datetime import date

from dateutil.relativedelta import relativedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Query, Session

from app.models.classificacao_abc import ClassificacaoABC
from app.models.consumo_tratado import ConsumoTratado
from app.models.importacoes import Importacao
from app.models.itens import Item
from app.models.modelo_treinado import ModeloTreinado
from app.models.previsoes import Previsao
from app.schemas.dashboard_schemas import (
    CoberturaPrevisao,
    ConsumoSetor,
    DistribuicaoABC,
    HierarquiaMaterial,
    ItemRanking,
    KpisResponse,
    MaterialFiltro,
    OpcoesFiltroResponse,
    PontoMensal,
    PrevisaoProximoMes,
)

# Teto de meses de uma série mensal (evita laços enormes com datas absurdas).
MAX_MESES_SERIE = 120


@dataclass
class FiltrosDashboard:
    """Filtros do dashboard. Competência = mês do consumo (primeiro dia do mês).
    Os demais filtros aceitam vários valores (lista vazia = sem filtro)."""

    data_inicio: date | None = None
    data_fim: date | None = None
    item_ids: list[int] = field(default_factory=list)
    grupos: list[str] = field(default_factory=list)
    subgrupos: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    setores: list[str] = field(default_factory=list)


def _aplicar_filtros(
    query: Query, empresa_id: int, filtros: FiltrosDashboard | None, *, com_datas: bool = True
) -> Query:
    """Restringe uma consulta sobre ConsumoTratado à empresa e aos filtros."""
    query = query.filter(ConsumoTratado.empresa_id == empresa_id)
    if filtros is None:
        return query
    if com_datas and filtros.data_inicio:
        query = query.filter(ConsumoTratado.periodo >= filtros.data_inicio.replace(day=1))
    if com_datas and filtros.data_fim:
        query = query.filter(ConsumoTratado.periodo <= filtros.data_fim.replace(day=1))
    if filtros.item_ids:
        query = query.filter(ConsumoTratado.item_id.in_(filtros.item_ids))
    if filtros.setores:
        query = query.filter(ConsumoTratado.setor.in_(filtros.setores))

    # Atributos do material: subconsulta nos itens (não duplica linhas como um join).
    condicoes = [Item.empresa_id == empresa_id]
    if filtros.grupos:
        condicoes.append(Item.grupo_material.in_(filtros.grupos))
    if filtros.subgrupos:
        condicoes.append(Item.subgrupo_material.in_(filtros.subgrupos))
    if filtros.classes:
        condicoes.append(Item.classe_material.in_(filtros.classes))
    if len(condicoes) > 1:
        query = query.filter(ConsumoTratado.item_id.in_(select(Item.id).where(*condicoes)))
    return query


def possui_dados(db: Session, empresa_id: int) -> bool:
    return (
        db.query(ConsumoTratado.id)
        .filter(ConsumoTratado.empresa_id == empresa_id)
        .first()
        is not None
    )


def cobertura_previsao(
    db: Session, empresa_id: int, filtros: FiltrosDashboard | None = None
) -> CoberturaPrevisao:
    """Dos itens consumidos no filtro, quantos têm previsão do modelo ativo, e que
    parcela do valor consumido eles representam (a métrica principal: itens de
    alto valor pesam mais que itens esporádicos de baixo valor)."""
    por_item = (
        _aplicar_filtros(
            db.query(ConsumoTratado.item_id, func.sum(ConsumoTratado.valor_total)),
            empresa_id,
            filtros,
        )
        .group_by(ConsumoTratado.item_id)
        .all()
    )
    com_previsao = {
        iid
        for (iid,) in db.query(Previsao.item_id)
        .join(ModeloTreinado, ModeloTreinado.id == Previsao.modelo_id)
        .filter(Previsao.empresa_id == empresa_id, ModeloTreinado.ativo.is_(True))
        .distinct()
        .all()
    }
    valor_total = sum(float(v) for _, v in por_item)
    cobertos = [(iid, float(v)) for iid, v in por_item if iid in com_previsao]
    valor_coberto = sum(v for _, v in cobertos)
    return CoberturaPrevisao(
        itens_consumidos=len(por_item),
        itens_com_previsao=len(cobertos),
        valor_total=valor_total,
        valor_coberto=valor_coberto,
        percentual_valor=round(valor_coberto / valor_total * 100, 1) if valor_total else 0.0,
        percentual_itens=round(len(cobertos) / len(por_item) * 100, 1) if por_item else 0.0,
    )


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
        cobertura_previsao=cobertura_previsao(db, empresa_id).percentual_valor,
    )


def ultima_importacao(db: Session, empresa_id: int):
    importacao = (
        db.query(Importacao)
        .filter(Importacao.empresa_id == empresa_id)
        .order_by(Importacao.criado_em.desc())
        .first()
    )
    return importacao.criado_em if importacao else None


def consumo_mensal(
    db: Session,
    empresa_id: int,
    *,
    meses: int = 12,
    filtros: FiltrosDashboard | None = None,
) -> list[PontoMensal]:
    """Série mensal contínua (meses sem consumo = 0).

    Sem competência informada, mostra os ``meses`` que terminam no último mês com
    dados (já filtrado). Com competência, usa exatamente o intervalo pedido.
    """
    linhas = (
        _aplicar_filtros(
            db.query(
                ConsumoTratado.periodo,
                func.sum(ConsumoTratado.quantidade_total),
                func.sum(ConsumoTratado.valor_total),
            ),
            empresa_id,
            filtros,
        )
        .group_by(ConsumoTratado.periodo)
        .order_by(ConsumoTratado.periodo)
        .all()
    )
    por_periodo = {p: (float(q), float(v)) for p, q, v in linhas}

    data_inicio = filtros.data_inicio.replace(day=1) if filtros and filtros.data_inicio else None
    data_fim = filtros.data_fim.replace(day=1) if filtros and filtros.data_fim else None
    if data_fim is None:
        if not por_periodo:
            return []
        data_fim = max(por_periodo)
    inicio = data_inicio or data_fim - relativedelta(months=meses - 1)
    inicio = max(inicio, data_fim - relativedelta(months=MAX_MESES_SERIE - 1))

    pontos: list[PontoMensal] = []
    atual = inicio
    while atual <= data_fim:
        quantidade, valor = por_periodo.get(atual, (0.0, 0.0))
        pontos.append(PontoMensal(periodo=atual, quantidade_total=quantidade, valor_total=valor))
        atual += relativedelta(months=1)
    return pontos


def consumo_por_setor(
    db: Session, empresa_id: int, filtros: FiltrosDashboard | None = None
) -> list[ConsumoSetor]:
    linhas = (
        _aplicar_filtros(
            db.query(
                ConsumoTratado.setor,
                func.sum(ConsumoTratado.quantidade_total),
                func.sum(ConsumoTratado.valor_total),
            ),
            empresa_id,
            filtros,
        )
        .group_by(ConsumoTratado.setor)
        .all()
    )
    return [
        ConsumoSetor(setor=setor, quantidade_total=float(q), valor_total=float(v))
        for setor, q, v in linhas
    ]


def previsao_proximo_mes(
    db: Session, empresa_id: int, filtros: FiltrosDashboard | None = None
) -> PrevisaoProximoMes:
    """Previsão do modelo mensal ativo para o próximo mês, somada entre os
    materiais do filtro.

    A previsão é por material (não por setor), então os filtros de competência e
    de setor não se aplicam; valem material, grupo, subgrupo e classe. O valor
    estimado usa o preço médio histórico de cada material (valor ÷ quantidade)."""
    filtros = filtros or FiltrosDashboard()
    modelo = (
        db.query(ModeloTreinado)
        .filter(ModeloTreinado.empresa_id == empresa_id, ModeloTreinado.ativo.is_(True))
        .first()
    )
    if modelo is None:
        return PrevisaoProximoMes(mes=None, quantidade_prevista=0.0, valor_estimado=0.0, itens_com_previsao=0)

    base = db.query(Previsao).filter(Previsao.empresa_id == empresa_id, Previsao.modelo_id == modelo.id)
    mes = base.with_entities(func.min(Previsao.periodo)).scalar()
    consulta = base.filter(Previsao.periodo == mes).with_entities(Previsao.item_id, Previsao.quantidade_prevista)
    if filtros.item_ids:
        consulta = consulta.filter(Previsao.item_id.in_(filtros.item_ids))
    condicoes = [Item.empresa_id == empresa_id]
    if filtros.grupos:
        condicoes.append(Item.grupo_material.in_(filtros.grupos))
    if filtros.subgrupos:
        condicoes.append(Item.subgrupo_material.in_(filtros.subgrupos))
    if filtros.classes:
        condicoes.append(Item.classe_material.in_(filtros.classes))
    if len(condicoes) > 1:
        consulta = consulta.filter(Previsao.item_id.in_(select(Item.id).where(*condicoes)))
    por_item = {item_id: float(qtd) for item_id, qtd in consulta.all()}

    precos = {
        iid: float(v) / float(q)
        for iid, q, v in db.query(
            ConsumoTratado.item_id,
            func.sum(ConsumoTratado.quantidade_total),
            func.sum(ConsumoTratado.valor_total),
        )
        .filter(ConsumoTratado.empresa_id == empresa_id, ConsumoTratado.item_id.in_(list(por_item)))
        .group_by(ConsumoTratado.item_id)
        .all()
        if q
    } if por_item else {}

    return PrevisaoProximoMes(
        mes=mes if por_item else None,
        quantidade_prevista=round(sum(por_item.values()), 3),
        valor_estimado=round(sum(q * precos.get(i, 0.0) for i, q in por_item.items()), 2),
        itens_com_previsao=len(por_item),
    )

def _tem_filtro(filtros: FiltrosDashboard | None) -> bool:
    return filtros is not None and any(bool(v) for v in vars(filtros).values())


def distribuicao_abc(
    db: Session, empresa_id: int, filtros: FiltrosDashboard | None = None
) -> list[DistribuicaoABC]:
    """Valor consumido e nº de itens (distintos) por classe ABC.

    Sem filtros, conta todos os itens classificados. Com filtros, só os itens que
    têm consumo dentro deles (ex.: no setor ou na competência escolhidos).
    """
    if not _tem_filtro(filtros):
        linhas = (
            db.query(
                ClassificacaoABC.classe,
                func.count(func.distinct(ClassificacaoABC.item_id)),
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

    linhas = (
        _aplicar_filtros(
            db.query(
                ClassificacaoABC.classe,
                func.count(func.distinct(ConsumoTratado.item_id)),
                func.coalesce(func.sum(ConsumoTratado.valor_total), 0.0),
            )
            .select_from(ConsumoTratado)
            .join(
                ClassificacaoABC,
                (ClassificacaoABC.item_id == ConsumoTratado.item_id)
                & (ClassificacaoABC.empresa_id == ConsumoTratado.empresa_id),
            ),
            empresa_id,
            filtros,
        )
        .group_by(ClassificacaoABC.classe)
        .order_by(ClassificacaoABC.classe)
        .all()
    )
    return [
        DistribuicaoABC(classe=classe, quantidade_itens=int(qtd), valor_total=float(valor))
        for classe, qtd, valor in linhas
    ]


def top_itens(
    db: Session,
    empresa_id: int,
    *,
    limite: int = 10,
    por: str = "valor",
    filtros: FiltrosDashboard | None = None,
) -> list[ItemRanking]:
    coluna = (
        func.sum(ConsumoTratado.valor_total)
        if por == "valor"
        else func.sum(ConsumoTratado.quantidade_total)
    )
    linhas = (
        _aplicar_filtros(
            db.query(
                Item.id,
                Item.codigo_item,
                Item.descricao_item,
                func.sum(ConsumoTratado.quantidade_total),
                func.sum(ConsumoTratado.valor_total),
            ).join(ConsumoTratado, ConsumoTratado.item_id == Item.id),
            empresa_id,
            filtros,
        )
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


def opcoes_filtro(db: Session, empresa_id: int) -> OpcoesFiltroResponse:
    """Valores existentes para popular os filtros: hierarquia do material,
    materiais (com atributos, para a cascata), setores e o intervalo de
    competências com consumo."""
    combinacoes = (
        db.query(Item.grupo_material, Item.subgrupo_material, Item.classe_material)
        .filter(Item.empresa_id == empresa_id)
        .distinct()
        .all()
    )
    hierarquia = sorted(
        (
            HierarquiaMaterial(grupo_material=g, subgrupo_material=s, classe_material=c)
            for g, s, c in combinacoes
            if g or s or c
        ),
        key=lambda h: (h.grupo_material or "", h.subgrupo_material or "", h.classe_material or ""),
    )
    materiais = [
        MaterialFiltro.model_validate(item, from_attributes=True)
        for item in db.query(Item)
        .filter(Item.empresa_id == empresa_id)
        .order_by(Item.descricao_item)
        .all()
    ]
    setores = [
        s
        for (s,) in db.query(ConsumoTratado.setor)
        .filter(ConsumoTratado.empresa_id == empresa_id, ConsumoTratado.setor.isnot(None))
        .distinct()
        .order_by(ConsumoTratado.setor)
        .all()
    ]
    inicio, fim = (
        db.query(func.min(ConsumoTratado.periodo), func.max(ConsumoTratado.periodo))
        .filter(ConsumoTratado.empresa_id == empresa_id)
        .first()
    )
    return OpcoesFiltroResponse(
        hierarquia=hierarquia,
        materiais=materiais,
        setores=setores,
        periodo_inicio=inicio,
        periodo_fim=fim,
    )
