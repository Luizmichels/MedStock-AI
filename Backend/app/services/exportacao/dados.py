"""Montagem dos relatórios (camada pura, testável) — RF10.

Cada função devolve um ``Relatorio``: a tabela principal resumida (uma linha por
material), indicadores para o topo do documento e, para o Excel, abas extras com
o detalhe. Sempre filtra por ``empresa_id`` (isolamento).
"""

from dataclasses import dataclass, field
from datetime import date

import pandas as pd
from dateutil.relativedelta import relativedelta
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.classificacao_abc import ClassificacaoABC
from app.models.consumo_tratado import ConsumoTratado
from app.models.itens import Item
from app.services.ml.predicao import resumo_mensal
from app.services.ml.treinamento import HORIZONTE_MESES

COLUNAS_PREVISOES = [
    "Código", "Descrição", "Unid.", "Curva ABC",
    *[f"Mês {i}" for i in range(1, HORIZONTE_MESES + 1)], f"Total {HORIZONTE_MESES} meses",
]
COLUNAS_CONSUMO = [
    "Código", "Descrição", "Unid.", "Grupo", "Curva ABC",
    "Quantidade", "Valor (R$)", "% do valor",
]
COLUNAS_CONSUMO_MENSAL = ["Código", "Descrição", "Competência", "Quantidade", "Valor (R$)"]
COLUNAS_CONSUMO_SETOR = ["Setor", "Quantidade", "Valor (R$)", "% do valor"]
COLUNAS_PREVISAO_MENSAL = [
    "Código", "Descrição", "Modelo", "Competência", "Previsão", "Mínimo", "Máximo",
    "Erro médio (MAE)",
]

# Colunas numéricas e quantas casas mostrar (usado no PDF e no Excel).
CASAS_DECIMAIS = {
    **{f"Mês {i}": 1 for i in range(1, HORIZONTE_MESES + 1)}, f"Total {HORIZONTE_MESES} meses": 1,
    "Quantidade": 2, "Valor (R$)": 2, "% do valor": 2,
    "Previsão": 1, "Mínimo": 1, "Máximo": 1, "Erro médio (MAE)": 1,
}
COLUNAS_MOEDA = {"Valor (R$)"}

# Nome de exibição dos algoritmos do modelo mensal.
ROTULOS_ALGORITMO = {
    "sma": "Média móvel (SMA)",
    "sarima": "ARIMA",
    "holt_winters": "Holt-Winters",
    "random_forest": "Random Forest",
    "gradient_boosting": "Gradient Boosting",
}


@dataclass
class Relatorio:
    titulo: str
    tabela: pd.DataFrame
    # Pares (rótulo, valor já formatado) exibidos no topo do relatório.
    indicadores: list[tuple[str, str]] = field(default_factory=list)
    # Linha de contexto abaixo do título (ex.: período ou data de referência).
    referencia: str = ""
    # Tabelas adicionais: no PDF aparecem antes da principal; no Excel viram abas.
    secoes: dict[str, pd.DataFrame] = field(default_factory=dict)
    # Abas só do Excel (detalhe completo).
    abas_extras: dict[str, pd.DataFrame] = field(default_factory=dict)
    nome_tabela: str = "Materiais"


def fmt_numero(valor: float, casas: int = 0) -> str:
    """1234.5 -> '1.234,50' (pt-BR)."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_moeda(valor: float) -> str:
    return f"R$ {fmt_numero(valor, 2)}"


def _fmt_data(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def _fmt_competencia(d: date) -> str:
    return d.strftime("%m/%Y")


def _classes_abc(db: Session, empresa_id: int) -> dict[int, str]:
    return dict(
        db.query(ClassificacaoABC.item_id, ClassificacaoABC.classe)
        .filter(ClassificacaoABC.empresa_id == empresa_id)
        .all()
    )


def _valor_por_item(db: Session, empresa_id: int) -> dict[int, float]:
    return {
        iid: float(v)
        for iid, v in db.query(ConsumoTratado.item_id, func.sum(ConsumoTratado.valor_total))
        .filter(ConsumoTratado.empresa_id == empresa_id)
        .group_by(ConsumoTratado.item_id)
        .all()
    }


_ORDEM_ABC = {"A": 0, "B": 1, "C": 2}


def montar_relatorio_previsoes(db: Session, empresa_id: int) -> Relatorio:
    """Uma linha por material com a previsão dos próximos meses do modelo ativo.
    O Excel traz também o detalhe mês a mês, com o modelo escolhido e a faixa.

    Ordenado por importância: curva ABC e, dentro dela, valor consumido."""
    resumo = resumo_mensal(db, empresa_id)
    itens_resumo = resumo["itens"]
    ids = [r["item_id"] for r in itens_resumo]
    itens = {
        i.id: i
        for i in db.query(Item).filter(Item.empresa_id == empresa_id, Item.id.in_(ids))
    } if ids else {}
    classes = _classes_abc(db, empresa_id)
    valores = _valor_por_item(db, empresa_id)

    def chave(r: dict):
        iid = r["item_id"]
        return (_ORDEM_ABC.get(classes.get(iid, ""), 3), -valores.get(iid, 0.0))

    linhas, detalhe = [], []
    for r in sorted(itens_resumo, key=chave):
        item = itens.get(r["item_id"])
        codigo = item.codigo_item if item else str(r["item_id"])
        descricao = item.descricao_item if item else ""
        meses = [p.quantidade_prevista for p in r["previsoes"]][:HORIZONTE_MESES]
        meses += [None] * (HORIZONTE_MESES - len(meses))
        linhas.append([
            codigo, descricao,
            (item.unidade_medida if item else None) or "—",
            classes.get(r["item_id"], "—"),
            *meses,
            r["total"],
        ])
        modelo = ROTULOS_ALGORITMO.get(r["algoritmo"], r["algoritmo"])
        for p in r["previsoes"]:
            detalhe.append([
                codigo, descricao, modelo, _fmt_competencia(p.periodo),
                p.quantidade_prevista, p.intervalo_inferior, p.intervalo_superior, r["mae"],
            ])
    tabela = pd.DataFrame(linhas, columns=COLUNAS_PREVISOES)

    contagem = tabela["Curva ABC"].value_counts().to_dict() if not tabela.empty else {}
    indicadores = [
        ("Materiais com previsão", fmt_numero(len(tabela))),
        ("Curva A", fmt_numero(contagem.get("A", 0))),
        ("Curva B", fmt_numero(contagem.get("B", 0))),
        ("Curva C", fmt_numero(contagem.get("C", 0))),
    ]
    if resumo["treinado_em"] is not None:
        indicadores.append(("Modelo treinado em", _fmt_data(resumo["treinado_em"])))

    referencia_mes = resumo["referencia"]
    if itens_resumo and referencia_mes is not None:
        rotulos = " · ".join(
            f"Mês {i} = {_fmt_competencia(referencia_mes + relativedelta(months=i))}"
            for i in range(1, HORIZONTE_MESES + 1)
        )
        referencia = f"{rotulos} (último mês com dados: {_fmt_competencia(referencia_mes)})"
    else:
        referencia = "Ainda não há previsões geradas. Treine os modelos na tela de Previsões."

    abas_extras = (
        {"Detalhe mensal": pd.DataFrame(detalhe, columns=COLUNAS_PREVISAO_MENSAL)} if detalhe else {}
    )
    return Relatorio(
        titulo="Relatório de Previsões",
        tabela=tabela,
        indicadores=indicadores,
        referencia=referencia,
        abas_extras=abas_extras,
    )


def montar_relatorio_consumo(
    db: Session,
    empresa_id: int,
    *,
    data_inicio: date | None = None,
    data_fim: date | None = None,
) -> Relatorio:
    """Consumo do período resumido por material (do maior para o menor valor),
    com um quadro por setor. O Excel traz também o detalhe mês a mês."""

    def filtrar(query):
        query = query.filter(ConsumoTratado.empresa_id == empresa_id)
        if data_inicio is not None:
            query = query.filter(ConsumoTratado.periodo >= data_inicio)
        if data_fim is not None:
            query = query.filter(ConsumoTratado.periodo <= data_fim)
        return query

    quantidade = func.sum(ConsumoTratado.quantidade_total)
    valor = func.sum(ConsumoTratado.valor_total)

    por_item = (
        filtrar(
            db.query(
                Item.id, Item.codigo_item, Item.descricao_item, Item.unidade_medida,
                Item.grupo_material, quantidade, valor,
            ).join(Item, Item.id == ConsumoTratado.item_id)
        )
        .group_by(Item.id, Item.codigo_item, Item.descricao_item, Item.unidade_medida, Item.grupo_material)
        .order_by(valor.desc())
        .all()
    )
    classes = _classes_abc(db, empresa_id)
    valor_total = sum(float(v) for *_, v in por_item)
    quantidade_total = sum(float(q) for *_, q, _v in por_item)

    def pct(v: float) -> float:
        return float(v) / valor_total * 100 if valor_total else 0.0

    tabela = pd.DataFrame(
        [
            [cod, desc, un or "—", grupo or "—", classes.get(iid, "—"), float(q), float(v), pct(v)]
            for iid, cod, desc, un, grupo, q, v in por_item
        ],
        columns=COLUNAS_CONSUMO,
    )

    por_setor = (
        filtrar(db.query(ConsumoTratado.setor, quantidade, valor))
        .group_by(ConsumoTratado.setor)
        .order_by(valor.desc())
        .all()
    )
    setores = pd.DataFrame(
        [[s or "Não informado", float(q), float(v), pct(v)] for s, q, v in por_setor],
        columns=COLUNAS_CONSUMO_SETOR,
    )

    mensal = (
        filtrar(
            db.query(Item.codigo_item, Item.descricao_item, ConsumoTratado.periodo, quantidade, valor)
            .join(Item, Item.id == ConsumoTratado.item_id)
        )
        .group_by(Item.codigo_item, Item.descricao_item, ConsumoTratado.periodo)
        .order_by(Item.codigo_item, ConsumoTratado.periodo)
        .all()
    )
    detalhe = pd.DataFrame(
        [[c, d, _fmt_competencia(p), float(q), float(v)] for c, d, p, q, v in mensal],
        columns=COLUNAS_CONSUMO_MENSAL,
    )

    periodos = [p for *_, p, _q, _v in mensal]
    inicio = data_inicio or (min(periodos) if periodos else None)
    fim = data_fim or (max(periodos) if periodos else None)
    referencia = (
        f"Competências de {_fmt_competencia(inicio)} a {_fmt_competencia(fim)}"
        if inicio and fim else "Todo o histórico"
    )
    indicadores = [
        ("Valor consumido", fmt_moeda(valor_total)),
        ("Quantidade consumida", fmt_numero(quantidade_total)),
        ("Materiais consumidos", fmt_numero(len(tabela))),
        ("Setores", fmt_numero(len(setores))),
    ]
    return Relatorio(
        titulo="Relatório de Consumo",
        tabela=tabela,
        indicadores=indicadores,
        referencia=referencia,
        secoes={"Consumo por setor": setores},
        abas_extras={"Detalhe mensal": detalhe},
    )
