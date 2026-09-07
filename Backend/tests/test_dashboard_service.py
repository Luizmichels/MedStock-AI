"""Testes do serviço de dashboard (RF09, RF12, RN07)."""

from datetime import date

from app.models.classificacao_abc import ClassificacaoABC
from app.models.consumo_tratado import ConsumoTratado
from app.models.importacoes import Importacao
from app.models.itens import Item
from app.services import dashboard_service as ds


def _item(db, empresa, codigo, *, ativo=True) -> Item:
    item = Item(empresa_id=empresa.id, codigo_item=codigo, descricao_item=f"Item {codigo}", ativo=ativo)
    db.add(item)
    db.flush()
    return item


def _tratado(db, empresa, item, periodo, qtd, valor, local="Central") -> None:
    db.add(ConsumoTratado(
        empresa_id=empresa.id, item_id=item.id, periodo=periodo,
        quantidade_total=qtd, valor_total=valor, local_estoque=local,
    ))


def _classe(db, empresa, item, classe) -> None:
    db.add(ClassificacaoABC(
        empresa_id=empresa.id, item_id=item.id, classe=classe, valor_acumulado_percentual=50.0,
    ))


def _importacao(db, empresa, usuario) -> Importacao:
    imp = Importacao(
        empresa_id=empresa.id, usuario_id=usuario.id,
        nome_arquivo="x.csv", tipo="csv", status="concluido",
    )
    db.add(imp)
    db.flush()
    return imp


def test_possui_dados_false_sem_dados(db_session, empresa):
    assert ds.possui_dados(db_session, empresa.id) is False


def test_possui_dados_true_com_tratado(db_session, empresa):
    item = _item(db_session, empresa, "MED001")
    _tratado(db_session, empresa, item, date(2024, 1, 1), 10, 100)
    db_session.commit()
    assert ds.possui_dados(db_session, empresa.id) is True


def test_kpis_conta_itens_ativos(db_session, empresa):
    _item(db_session, empresa, "A", ativo=True)
    _item(db_session, empresa, "B", ativo=False)
    db_session.commit()
    kpis = ds.calcular_kpis(db_session, empresa.id)
    assert kpis.total_itens_ativos == 1


def test_kpis_soma_valor_total(db_session, empresa):
    item = _item(db_session, empresa, "A")
    _tratado(db_session, empresa, item, date(2024, 1, 1), 10, 100)
    _tratado(db_session, empresa, item, date(2024, 2, 1), 10, 150)
    db_session.commit()
    kpis = ds.calcular_kpis(db_session, empresa.id)
    assert kpis.valor_total_consumido == 250


def test_kpis_conta_classe_a(db_session, empresa):
    a = _item(db_session, empresa, "A")
    b = _item(db_session, empresa, "B")
    _classe(db_session, empresa, a, "A")
    _classe(db_session, empresa, b, "C")
    db_session.commit()
    kpis = ds.calcular_kpis(db_session, empresa.id)
    assert kpis.itens_classe_a == 1


def test_kpis_cobertura_previsao(db_session, empresa):
    elegivel = _item(db_session, empresa, "LONGO")
    for mes in range(1, 7):
        _tratado(db_session, empresa, elegivel, date(2024, mes, 1), 10, 100)
    curto = _item(db_session, empresa, "CURTO")
    _tratado(db_session, empresa, curto, date(2024, 1, 1), 10, 100)
    db_session.commit()
    kpis = ds.calcular_kpis(db_session, empresa.id)
    assert kpis.cobertura_previsao == 50.0


def test_kpis_isolados_por_empresa(db_session, empresa, empresa_secundaria):
    _item(db_session, empresa, "E1", ativo=True)
    _item(db_session, empresa_secundaria, "E2", ativo=True)
    db_session.commit()
    assert ds.calcular_kpis(db_session, empresa.id).total_itens_ativos == 1


def test_consumo_mensal_preenche_meses_sem_movimento(db_session, empresa):
    item = _item(db_session, empresa, "A")
    _tratado(db_session, empresa, item, date(2024, 1, 1), 10, 100)
    _tratado(db_session, empresa, item, date(2024, 3, 1), 30, 300)  # pula fevereiro
    db_session.commit()

    pontos = ds.consumo_mensal(db_session, empresa.id, meses=3)
    assert [p.periodo for p in pontos] == [date(2024, 1, 1), date(2024, 2, 1), date(2024, 3, 1)]
    assert pontos[1].quantidade_total == 0.0


def test_consumo_mensal_sem_dados_retorna_vazio(db_session, empresa):
    assert ds.consumo_mensal(db_session, empresa.id) == []


def test_consumo_por_local_agrega(db_session, empresa):
    item = _item(db_session, empresa, "A")
    _tratado(db_session, empresa, item, date(2024, 1, 1), 10, 100, local="Central")
    _tratado(db_session, empresa, item, date(2024, 2, 1), 5, 50, local="Farmácia")
    db_session.commit()
    locais = {c.local_estoque for c in ds.consumo_por_local(db_session, empresa.id)}
    assert locais == {"Central", "Farmácia"}


def test_distribuicao_abc_conta_por_classe(db_session, empresa):
    a1 = _item(db_session, empresa, "A1")
    a2 = _item(db_session, empresa, "A2")
    _classe(db_session, empresa, a1, "A")
    _classe(db_session, empresa, a2, "A")
    db_session.commit()
    dist = {d.classe: d.quantidade_itens for d in ds.distribuicao_abc(db_session, empresa.id)}
    assert dist["A"] == 2


def test_top_itens_ordena_por_valor(db_session, empresa):
    caro = _item(db_session, empresa, "CARO")
    barato = _item(db_session, empresa, "BARATO")
    _tratado(db_session, empresa, caro, date(2024, 1, 1), 1, 1000)
    _tratado(db_session, empresa, barato, date(2024, 1, 1), 1, 10)
    db_session.commit()
    ranking = ds.top_itens(db_session, empresa.id, por="valor")
    assert ranking[0].codigo_item == "CARO"


def test_top_itens_respeita_limite(db_session, empresa):
    for i in range(5):
        item = _item(db_session, empresa, f"COD{i}")
        _tratado(db_session, empresa, item, date(2024, 1, 1), 1, 10 * (i + 1))
    db_session.commit()
    assert len(ds.top_itens(db_session, empresa.id, limite=2)) == 2


def test_ultima_importacao_retorna_mais_recente(db_session, empresa, usuario_admin):
    _importacao(db_session, empresa, usuario_admin)
    db_session.commit()
    assert ds.ultima_importacao(db_session, empresa.id) is not None
