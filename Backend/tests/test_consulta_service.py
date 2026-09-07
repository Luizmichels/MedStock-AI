"""Testes da camada de consulta (RF03)."""

from datetime import date

from app.models.classificacao_abc import ClassificacaoABC
from app.models.consumo import Consumo
from app.models.importacoes import Importacao
from app.models.itens import Item
from app.services import consulta_service as cs


def _item(db, empresa, codigo, descricao="Item genérico") -> Item:
    item = Item(empresa_id=empresa.id, codigo_item=codigo, descricao_item=descricao)
    db.add(item)
    db.flush()
    return item


def _classe(db, empresa, item, classe: str) -> None:
    db.add(ClassificacaoABC(
        empresa_id=empresa.id, item_id=item.id, classe=classe,
        valor_acumulado_percentual=50.0,
    ))


def _importacao(db, empresa, usuario) -> Importacao:
    imp = Importacao(
        empresa_id=empresa.id, usuario_id=usuario.id,
        nome_arquivo="x.csv", tipo="csv", status="concluido",
    )
    db.add(imp)
    db.flush()
    return imp


def _consumo(db, empresa, item, imp, data_, *, qtd=1.0, valor=1.0, local="Central") -> None:
    db.add(Consumo(
        empresa_id=empresa.id, importacao_id=imp.id, item_id=item.id,
        data=data_, quantidade=qtd, valor=valor, local_estoque=local,
    ))


# --------------------------------------------------------------------------- #
# Itens
# --------------------------------------------------------------------------- #
def test_listar_itens_retorna_item_com_classe_abc(db_session, empresa):
    item = _item(db_session, empresa, "MED001")
    _classe(db_session, empresa, item, "A")
    db_session.commit()

    pagina = cs.listar_itens(db_session, empresa.id)
    assert pagina.total == 1
    assert pagina.itens[0].classe_abc == "A"


def test_listar_itens_filtra_por_busca(db_session, empresa):
    _item(db_session, empresa, "MED001", "Dipirona")
    _item(db_session, empresa, "MED002", "Soro Fisiológico")
    db_session.commit()

    pagina = cs.listar_itens(db_session, empresa.id, busca="soro")
    assert pagina.total == 1
    assert pagina.itens[0].codigo_item == "MED002"


def test_listar_itens_filtra_por_classe_abc(db_session, empresa):
    a = _item(db_session, empresa, "A1")
    b = _item(db_session, empresa, "B1")
    _classe(db_session, empresa, a, "A")
    _classe(db_session, empresa, b, "B")
    db_session.commit()

    pagina = cs.listar_itens(db_session, empresa.id, classe_abc="A")
    assert [i.codigo_item for i in pagina.itens] == ["A1"]


def test_listar_itens_isolado_por_empresa(db_session, empresa, empresa_secundaria):
    _item(db_session, empresa, "E1")
    _item(db_session, empresa_secundaria, "E2")
    db_session.commit()

    pagina = cs.listar_itens(db_session, empresa.id)
    assert pagina.total == 1
    assert pagina.itens[0].codigo_item == "E1"


def test_paginacao_respeita_tamanho(db_session, empresa):
    for i in range(5):
        _item(db_session, empresa, f"COD{i}")
    db_session.commit()

    pagina = cs.listar_itens(db_session, empresa.id, pagina=1, tamanho=2)
    assert len(pagina.itens) == 2
    assert pagina.total == 5
    assert pagina.tamanho == 2


# --------------------------------------------------------------------------- #
# Consumos
# --------------------------------------------------------------------------- #
def test_listar_consumos_isolado_por_empresa(db_session, empresa, empresa_secundaria, usuario_admin):
    item1 = _item(db_session, empresa, "E1")
    imp1 = _importacao(db_session, empresa, usuario_admin)
    _consumo(db_session, empresa, item1, imp1, date(2024, 1, 1))

    item2 = _item(db_session, empresa_secundaria, "E2")
    imp2 = Importacao(
        empresa_id=empresa_secundaria.id, usuario_id=usuario_admin.id,
        nome_arquivo="y.csv", tipo="csv", status="concluido",
    )
    db_session.add(imp2)
    db_session.flush()
    _consumo(db_session, empresa_secundaria, item2, imp2, date(2024, 1, 1))
    db_session.commit()

    pagina = cs.listar_consumos(db_session, empresa.id)
    assert pagina.total == 1


def test_listar_consumos_filtra_por_intervalo_de_data(db_session, empresa, item, usuario_admin):
    imp = _importacao(db_session, empresa, usuario_admin)
    _consumo(db_session, empresa, item, imp, date(2024, 1, 15))
    _consumo(db_session, empresa, item, imp, date(2024, 3, 10))
    db_session.commit()

    pagina = cs.listar_consumos(
        db_session, empresa.id, data_inicio=date(2024, 2, 1), data_fim=date(2024, 12, 31)
    )
    assert pagina.total == 1
    assert pagina.itens[0].data == date(2024, 3, 10)


# --------------------------------------------------------------------------- #
# Série temporal e histórico
# --------------------------------------------------------------------------- #
def test_serie_temporal_ordenada_por_periodo(db_session, empresa, item, serie_consumo):
    serie = cs.obter_serie_temporal(db_session, empresa.id, item.id)
    periodos = [p.periodo for p in serie]
    assert len(serie) == 18
    assert periodos == sorted(periodos)


def test_contar_meses_de_historico(db_session, empresa, item, serie_consumo):
    assert cs.contar_meses_de_historico(db_session, empresa.id, item.id) == 18
