"""Testes do pipeline de previsão diária."""

from datetime import date, timedelta

from app.models.consumo import Consumo
from app.models.importacoes import Importacao
from app.models.previsao_diaria import PrevisaoDiaria
from app.services.ml import previsao_diaria as diaria


def _importacao(db, empresa, usuario) -> Importacao:
    imp = Importacao(
        empresa_id=empresa.id, usuario_id=usuario.id,
        nome_arquivo="x.csv", tipo="csv", status="concluido",
    )
    db.add(imp)
    db.flush()
    return imp


def _consumo(db, empresa, imp, item_id, dia, qtd):
    db.add(Consumo(
        empresa_id=empresa.id, importacao_id=imp.id, item_id=item_id,
        data=dia, quantidade=qtd, valor=qtd, local_estoque="Central",
    ))


def test_carregar_series_diarias_preenche_zeros_e_referencia_comum(
    db_session, empresa, usuario_admin, item
):
    imp = _importacao(db_session, empresa, usuario_admin)
    _consumo(db_session, empresa, imp, item.id, date(2024, 1, 1), 10)
    _consumo(db_session, empresa, imp, item.id, date(2024, 1, 5), 20)  # buraco 2-4
    db_session.commit()

    series = diaria.carregar_series_diarias(db_session, empresa.id)
    assert len(series) == 1
    s = series[0]
    assert s.inicio == date(2024, 1, 1)
    assert s.referencia == date(2024, 1, 5)
    assert list(s.valores) == [10.0, 0.0, 0.0, 0.0, 20.0]


def test_prever_item_regular_usa_media_movel_sazonal(db_session, empresa, usuario_admin, item):
    imp = _importacao(db_session, empresa, usuario_admin)
    inicio = date(2024, 1, 1)
    for i in range(40):  # consumo denso todo dia -> demanda regular (suave)
        _consumo(db_session, empresa, imp, item.id, inicio + timedelta(days=i), 10)
    db_session.commit()

    series = diaria.carregar_series_diarias(db_session, empresa.id)
    previsoes, metodo = diaria.prever_item(series[0])
    assert metodo == "media_movel_sazonal"
    assert len(previsoes) == diaria.HORIZONTE_DIARIO
    assert all(v >= 0 for v in previsoes)
    assert sum(previsoes) > 0


def test_prever_item_intermitente_usa_croston(db_session, empresa, usuario_admin, item):
    imp = _importacao(db_session, empresa, usuario_admin)
    inicio = date(2024, 1, 1)
    for semana in range(8):  # demanda a cada 5 dias -> intermitente
        _consumo(db_session, empresa, imp, item.id, inicio + timedelta(days=semana * 5), 5)
    db_session.commit()

    series = diaria.carregar_series_diarias(db_session, empresa.id)
    _prev, metodo = diaria.prever_item(series[0])
    assert metodo == "croston_sba"


def test_gerar_previsoes_diarias_persiste_e_filtra_curto(
    db_session, empresa, usuario_admin, item
):
    imp = _importacao(db_session, empresa, usuario_admin)
    inicio = date(2024, 1, 1)
    for i in range(40):  # item elegível: 40 dias de histórico
        _consumo(db_session, empresa, imp, item.id, inicio + timedelta(days=i), 10)
    # segundo item, histórico curto (< DIAS_MINIMOS) -> não deve ser previsto
    from app.models.itens import Item
    curto = Item(empresa_id=empresa.id, codigo_item="CURTO", descricao_item="Curto")
    db_session.add(curto)
    db_session.flush()
    for i in range(5):
        _consumo(db_session, empresa, imp, curto.id, inicio + timedelta(days=i), 3)
    db_session.commit()

    n = diaria.gerar_previsoes_diarias(db_session, empresa.id)
    assert n == 1  # só o item longo
    pontos = db_session.query(PrevisaoDiaria).filter(
        PrevisaoDiaria.empresa_id == empresa.id
    ).all()
    assert len(pontos) == diaria.HORIZONTE_DIARIO
    assert {p.item_id for p in pontos} == {item.id}
    # todos os dias previstos são futuros (após a referência)
    assert all(p.data > date(2024, 2, 9) for p in pontos)


def test_resumo_por_item_soma_horizontes(db_session, empresa, usuario_admin, item):
    imp = _importacao(db_session, empresa, usuario_admin)
    inicio = date(2024, 1, 1)
    for i in range(40):
        _consumo(db_session, empresa, imp, item.id, inicio + timedelta(days=i), 10)
    db_session.commit()
    diaria.gerar_previsoes_diarias(db_session, empresa.id)

    resumo = diaria.resumo_por_item(db_session, empresa.id)
    assert len(resumo) == 1
    r = resumo[0]
    assert r["item_id"] == item.id
    # coerência entre horizontes: 7 <= 15 <= 30
    assert r["sete_dias"] <= r["quinze_dias"] <= r["trinta_dias"]
    assert r["proximo_dia"] > 0


def test_gerar_previsoes_diarias_regenera(db_session, empresa, usuario_admin, item):
    imp = _importacao(db_session, empresa, usuario_admin)
    inicio = date(2024, 1, 1)
    for i in range(40):
        _consumo(db_session, empresa, imp, item.id, inicio + timedelta(days=i), 10)
    db_session.commit()

    diaria.gerar_previsoes_diarias(db_session, empresa.id)
    diaria.gerar_previsoes_diarias(db_session, empresa.id)
    pontos = db_session.query(PrevisaoDiaria).filter(
        PrevisaoDiaria.empresa_id == empresa.id
    ).count()
    assert pontos == diaria.HORIZONTE_DIARIO  # não duplicou
