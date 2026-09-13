"""Testes de orquestração do treino e geração de previsões (estimador fake)."""

from datetime import date

import numpy as np
import pytest

from app.models.consumo_tratado import ConsumoTratado
from app.models.itens import Item
from app.models.modelo_treinado import ModeloTreinado
from app.models.previsoes import Previsao
from app.services.ml import predicao, treinamento
from app.services.ml.estimadores import ALGORITMOS
from tests.ml.fakes import EstimadorFake, fabrica_fake


def _item_curto(db, empresa, codigo="CURTO") -> Item:
    item = Item(empresa_id=empresa.id, codigo_item=codigo, descricao_item="Curto")
    db.add(item)
    db.flush()
    for mes in (1, 2):
        db.add(ConsumoTratado(
            empresa_id=empresa.id, item_id=item.id, periodo=date(2024, mes, 1),
            quantidade_total=10.0, valor_total=100.0, local_estoque=None,
        ))
    db.commit()
    return item


def test_carregar_series_preenche_meses_faltantes_com_zero(db_session, empresa, item):
    # Consumo em jan e mar, sem fevereiro: o mês faltante deve virar zero.
    db_session.add(ConsumoTratado(
        empresa_id=empresa.id, item_id=item.id, periodo=date(2024, 1, 1),
        quantidade_total=10.0, valor_total=100.0, local_estoque=None,
    ))
    db_session.add(ConsumoTratado(
        empresa_id=empresa.id, item_id=item.id, periodo=date(2024, 3, 1),
        quantidade_total=30.0, valor_total=300.0, local_estoque=None,
    ))
    db_session.commit()

    serie = treinamento.carregar_series_por_item(db_session, empresa.id)[item.id]
    assert list(serie) == [10.0, 0.0, 30.0]


def test_treinar_empresa_persiste_modelo_ativo(db_session, empresa, item, serie_consumo):
    modelo = treinamento.treinar_empresa(db_session, empresa.id, fabrica=fabrica_fake)
    assert modelo.id is not None
    assert modelo.algoritmo == "melhor_por_item"
    assert modelo.ativo is True


def test_selecionar_algoritmo_por_item_um_por_item():
    series = {
        1: np.array([10, 12, 11, 13, 12, 14, 13, 15, 14, 16, 15, 17], dtype=float),
        2: np.array([5, 6, 5, 7, 6, 8, 7, 9, 8, 10, 9, 11], dtype=float),
    }
    selecao = treinamento.selecionar_algoritmo_por_item(series, fabrica=fabrica_fake)
    assert set(selecao) == {1, 2}
    assert all(r.algoritmo in ALGORITMOS for r in selecao.values())


def test_treinar_empresa_registra_selecao_por_item(db_session, empresa, item, serie_consumo):
    modelo = treinamento.treinar_empresa(db_session, empresa.id, fabrica=fabrica_fake)
    assert modelo.parametros["selecao"] == "por_item"
    assert str(item.id) in modelo.parametros["itens"]
    assert modelo.parametros["itens"][str(item.id)]["algoritmo"] in ALGORITMOS


def test_gerar_previsoes_usa_algoritmo_escolhido_do_item(db_session, empresa, item, serie_consumo):
    modelo = treinamento.treinar_empresa(db_session, empresa.id, fabrica=fabrica_fake)
    # Fixa a escolha do item num algoritmo conhecido.
    modelo.parametros = {"selecao": "por_item", "itens": {str(item.id): {"algoritmo": "sarima"}}}

    usados = []

    def fabrica_registradora(algoritmo):
        usados.append(algoritmo)
        return EstimadorFake()

    predicao.gerar_previsoes(db_session, empresa.id, modelo, fabrica=fabrica_registradora)
    assert usados == ["sarima"]


def test_treinar_empresa_sem_itens_elegiveis_levanta(db_session, empresa):
    with pytest.raises(ValueError):
        treinamento.treinar_empresa(db_session, empresa.id, fabrica=fabrica_fake)


def test_treinar_empresa_desativa_modelo_anterior(db_session, empresa, item, serie_consumo):
    treinamento.treinar_empresa(db_session, empresa.id, fabrica=fabrica_fake)
    treinamento.treinar_empresa(db_session, empresa.id, fabrica=fabrica_fake)

    ativos = db_session.query(ModeloTreinado).filter(
        ModeloTreinado.empresa_id == empresa.id, ModeloTreinado.ativo.is_(True)
    ).count()
    total = db_session.query(ModeloTreinado).filter(
        ModeloTreinado.empresa_id == empresa.id
    ).count()
    assert ativos == 1
    assert total == 2


def test_ativar_modelo_troca_ativo(db_session, empresa):
    m1 = ModeloTreinado(empresa_id=empresa.id, algoritmo="sma", ativo=True)
    m2 = ModeloTreinado(empresa_id=empresa.id, algoritmo="sarima", ativo=False)
    db_session.add_all([m1, m2])
    db_session.commit()

    ativado = treinamento.ativar_modelo(db_session, empresa.id, m2.id)
    assert ativado.id == m2.id
    db_session.refresh(m1)
    assert m1.ativo is False
    assert m2.ativo is True


def test_ativar_modelo_inexistente_retorna_none(db_session, empresa):
    assert treinamento.ativar_modelo(db_session, empresa.id, 99999) is None


def test_gerar_previsoes_cria_horizonte(db_session, empresa, item, serie_consumo):
    modelo = treinamento.treinar_empresa(db_session, empresa.id, fabrica=fabrica_fake)
    previsoes = predicao.gerar_previsoes(db_session, empresa.id, modelo, horizonte=6, fabrica=fabrica_fake)

    assert len(previsoes) == 6
    ultimo_historico = date(2025, 6, 1)  # jan/2024 + 17 meses
    assert all(p.periodo > ultimo_historico for p in previsoes)


def test_gerar_previsoes_regenera_substitui_anteriores(db_session, empresa, item, serie_consumo):
    modelo = treinamento.treinar_empresa(db_session, empresa.id, fabrica=fabrica_fake)
    predicao.gerar_previsoes(db_session, empresa.id, modelo, horizonte=6, fabrica=fabrica_fake)
    predicao.gerar_previsoes(db_session, empresa.id, modelo, horizonte=6, fabrica=fabrica_fake)

    total = db_session.query(Previsao).filter(Previsao.empresa_id == empresa.id).count()
    assert total == 6


def test_gerar_previsoes_nao_preve_item_omitido(db_session, empresa, item, serie_consumo):
    curto = _item_curto(db_session, empresa)
    modelo = treinamento.treinar_empresa(db_session, empresa.id, fabrica=fabrica_fake)
    predicao.gerar_previsoes(db_session, empresa.id, modelo, horizonte=6, fabrica=fabrica_fake)

    previsoes_curto = db_session.query(Previsao).filter(
        Previsao.empresa_id == empresa.id, Previsao.item_id == curto.id
    ).count()
    assert previsoes_curto == 0
