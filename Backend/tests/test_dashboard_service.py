"""Testes do serviço de dashboard (RF09, RF12, RN07)."""

from datetime import date

from app.models.classificacao_abc import ClassificacaoABC
from app.models.consumo_tratado import ConsumoTratado
from app.models.importacoes import Importacao
from app.models.itens import Item
from app.models.previsao_diaria import PrevisaoDiaria
from app.services import dashboard_service as ds


def _item(db, empresa, codigo, *, ativo=True) -> Item:
    item = Item(empresa_id=empresa.id, codigo_item=codigo, descricao_item=f"Item {codigo}", ativo=ativo)
    db.add(item)
    db.flush()
    return item


def _tratado(db, empresa, item, periodo, qtd, valor, setor="Central") -> None:
    db.add(ConsumoTratado(
        empresa_id=empresa.id, item_id=item.id, periodo=periodo,
        quantidade_total=qtd, valor_total=valor, setor=setor,
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


def _previsao_diaria(db, empresa, item) -> None:
    db.add(PrevisaoDiaria(
        empresa_id=empresa.id, item_id=item.id, data=date(2024, 7, 1),
        quantidade_prevista=1.0, metodo="croston_sba",
    ))


def test_cobertura_previsao_pondera_pelo_valor(db_session, empresa):
    caro = _item(db_session, empresa, "CARO")
    barato = _item(db_session, empresa, "BARATO")
    _tratado(db_session, empresa, caro, date(2024, 1, 1), 10, 900, setor="UTI")
    _tratado(db_session, empresa, barato, date(2024, 1, 1), 10, 100, setor="Farmácia")
    _previsao_diaria(db_session, empresa, caro)
    db_session.commit()

    cobertura = ds.cobertura_previsao(db_session, empresa.id)
    assert (cobertura.itens_consumidos, cobertura.itens_com_previsao) == (2, 1)
    assert cobertura.percentual_valor == 90.0
    assert cobertura.percentual_itens == 50.0
    assert ds.calcular_kpis(db_session, empresa.id).cobertura_previsao == 90.0

    # Respeita os filtros: no setor Farmácia só há o item sem previsão.
    so_farmacia = ds.cobertura_previsao(db_session, empresa.id, ds.FiltrosDashboard(setores=["Farmácia"]))
    assert so_farmacia.percentual_valor == 0.0


def test_cobertura_previsao_sem_consumo(db_session, empresa):
    cobertura = ds.cobertura_previsao(db_session, empresa.id)
    assert cobertura.percentual_valor == 0.0 and cobertura.itens_consumidos == 0


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


def test_consumo_por_setor_agrega(db_session, empresa):
    item = _item(db_session, empresa, "A")
    _tratado(db_session, empresa, item, date(2024, 1, 1), 10, 100, setor="Central")
    _tratado(db_session, empresa, item, date(2024, 2, 1), 5, 50, setor="Farmácia")
    db_session.commit()
    locais = {c.setor for c in ds.consumo_por_setor(db_session, empresa.id)}
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


# --------------------------------------------------------------------------- #
# Filtros (competência, material, grupo/subgrupo/classe, setor)
# --------------------------------------------------------------------------- #
def _item_material(db, empresa, codigo, grupo, subgrupo=None, classe=None) -> Item:
    item = Item(
        empresa_id=empresa.id, codigo_item=codigo, descricao_item=f"Item {codigo}",
        grupo_material=grupo, subgrupo_material=subgrupo, classe_material=classe,
    )
    db.add(item)
    db.flush()
    return item


def test_consumo_mensal_filtra_por_setor_e_grupo(db_session, empresa):
    med = _item_material(db_session, empresa, "MED", "Medicamentos")
    mat = _item_material(db_session, empresa, "MAT", "Materiais")
    _tratado(db_session, empresa, med, date(2024, 1, 1), 10, 100, setor="UTI")
    _tratado(db_session, empresa, med, date(2024, 1, 1), 5, 50, setor="Farmácia")
    _tratado(db_session, empresa, mat, date(2024, 1, 1), 7, 70, setor="UTI")
    db_session.commit()

    por_setor = ds.consumo_mensal(db_session, empresa.id, filtros=ds.FiltrosDashboard(setores=["UTI"]))
    assert por_setor[-1].valor_total == 170

    por_grupo = ds.consumo_mensal(
        db_session, empresa.id, filtros=ds.FiltrosDashboard(grupos=["Medicamentos"])
    )
    assert por_grupo[-1].valor_total == 150

    combinado = ds.consumo_mensal(
        db_session, empresa.id,
        filtros=ds.FiltrosDashboard(grupos=["Medicamentos"], setores=["UTI"]),
    )
    assert combinado[-1].valor_total == 100


def test_consumo_mensal_competencia_gera_intervalo_continuo(db_session, empresa):
    item = _item(db_session, empresa, "X")
    _tratado(db_session, empresa, item, date(2024, 2, 1), 10, 100)
    db_session.commit()

    pontos = ds.consumo_mensal(
        db_session, empresa.id,
        filtros=ds.FiltrosDashboard(data_inicio=date(2024, 1, 1), data_fim=date(2024, 4, 1)),
    )
    assert [p.periodo for p in pontos] == [
        date(2024, 1, 1), date(2024, 2, 1), date(2024, 3, 1), date(2024, 4, 1),
    ]
    assert [p.valor_total for p in pontos] == [0, 100, 0, 0]


def test_distribuicao_abc_conta_item_uma_vez_mesmo_com_varios_meses(db_session, empresa):
    item = _item(db_session, empresa, "A1")
    _classe(db_session, empresa, item, "A")
    for mes in (1, 2, 3):
        _tratado(db_session, empresa, item, date(2024, mes, 1), 10, 100)
    db_session.commit()

    dist = {d.classe: d for d in ds.distribuicao_abc(db_session, empresa.id)}
    assert dist["A"].quantidade_itens == 1  # antes saía 3 (uma linha por mês)
    assert dist["A"].valor_total == 300


def test_distribuicao_abc_com_filtro_considera_so_itens_do_filtro(db_session, empresa):
    uti = _item(db_session, empresa, "U")
    farm = _item(db_session, empresa, "F")
    _classe(db_session, empresa, uti, "A")
    _classe(db_session, empresa, farm, "A")
    _tratado(db_session, empresa, uti, date(2024, 1, 1), 10, 100, setor="UTI")
    _tratado(db_session, empresa, farm, date(2024, 1, 1), 10, 40, setor="Farmácia")
    db_session.commit()

    dist = ds.distribuicao_abc(db_session, empresa.id, ds.FiltrosDashboard(setores=["UTI"]))
    assert [(d.classe, d.quantidade_itens, d.valor_total) for d in dist] == [("A", 1, 100)]


def test_consumo_por_setor_respeita_filtro_de_material(db_session, empresa):
    a = _item(db_session, empresa, "A")
    b = _item(db_session, empresa, "B")
    _tratado(db_session, empresa, a, date(2024, 1, 1), 1, 10, setor="UTI")
    _tratado(db_session, empresa, b, date(2024, 1, 1), 1, 20, setor="Farmácia")
    db_session.commit()

    setores = ds.consumo_por_setor(db_session, empresa.id, ds.FiltrosDashboard(item_ids=[a.id]))
    assert [(s.setor, s.valor_total) for s in setores] == [("UTI", 10)]


def test_opcoes_filtro_lista_hierarquia_setores_e_periodo(db_session, empresa):
    item = _item_material(db_session, empresa, "M1", "Medicamentos", "Analgésicos", "Injetáveis")
    _item(db_session, empresa, "SEM")  # sem atributos: não entra na hierarquia
    _tratado(db_session, empresa, item, date(2024, 1, 1), 1, 10, setor="UTI")
    _tratado(db_session, empresa, item, date(2024, 3, 1), 1, 10, setor="Farmácia")
    db_session.commit()

    opcoes = ds.opcoes_filtro(db_session, empresa.id)
    assert [(h.grupo_material, h.subgrupo_material, h.classe_material) for h in opcoes.hierarquia] == [
        ("Medicamentos", "Analgésicos", "Injetáveis"),
    ]
    assert opcoes.setores == ["Farmácia", "UTI"]
    assert opcoes.periodo_inicio == date(2024, 1, 1)
    assert opcoes.periodo_fim == date(2024, 3, 1)
    # Todos os materiais (inclusive sem atributos), com os atributos para a cascata.
    assert [(m.codigo_item, m.grupo_material, m.classe_material) for m in opcoes.materiais] == [
        ("M1", "Medicamentos", "Injetáveis"),
        ("SEM", None, None),
    ]


def test_filtros_aceitam_varios_valores(db_session, empresa):
    a = _item_material(db_session, empresa, "A", "Medicamentos")
    b = _item_material(db_session, empresa, "B", "Materiais")
    c = _item_material(db_session, empresa, "C", "Nutrição")
    for item, valor in ((a, 10), (b, 20), (c, 40)):
        _tratado(db_session, empresa, item, date(2024, 1, 1), 1, valor, setor=item.codigo_item)
    db_session.commit()

    def total(filtros):
        return sum(p.valor_total for p in ds.consumo_mensal(db_session, empresa.id, filtros=filtros))

    assert total(ds.FiltrosDashboard(grupos=["Medicamentos", "Materiais"])) == 30
    assert total(ds.FiltrosDashboard(setores=["A", "C"])) == 50
    assert total(ds.FiltrosDashboard(item_ids=[b.id, c.id])) == 60
    assert total(ds.FiltrosDashboard(grupos=["Medicamentos", "Materiais"], setores=["B", "C"])) == 20


def _previsao_dias(db, empresa, item, valores) -> None:
    for i, v in enumerate(valores):
        db.add(PrevisaoDiaria(
            empresa_id=empresa.id, item_id=item.id, data=date(2024, 7, 1 + i),
            quantidade_prevista=v, metodo="croston_sba",
        ))


def test_previsao_proximos_dias_soma_quantidade_e_estima_valor(db_session, empresa):
    remedio = _item_material(db_session, empresa, "R1", "Medicamentos")
    luva = _item_material(db_session, empresa, "L1", "Materiais")
    _tratado(db_session, empresa, remedio, date(2024, 6, 1), 10, 50)  # R$ 5 por unidade
    _tratado(db_session, empresa, luva, date(2024, 6, 1), 4, 4)  # R$ 1 por unidade
    _previsao_dias(db_session, empresa, remedio, [2.0] * 31)
    _previsao_dias(db_session, empresa, luva, [1.0] * 10)
    db_session.commit()

    tudo = ds.previsao_proximos_dias(db_session, empresa.id)
    assert tudo.quantidade_prevista == 70.0  # 30 dias x 2 + 10 x 1 (o 31º dia fica de fora)
    assert tudo.valor_estimado == 310.0  # 60 x 5 + 10 x 1
    assert tudo.itens_com_previsao == 2
    assert tudo.base == date(2024, 6, 30)

    so_remedio = ds.previsao_proximos_dias(db_session, empresa.id, ds.FiltrosDashboard(grupos=["Medicamentos"]))
    assert (so_remedio.quantidade_prevista, so_remedio.itens_com_previsao) == (60.0, 1)
    sete = ds.previsao_proximos_dias(db_session, empresa.id, dias=7)
    assert sete.quantidade_prevista == 21.0


def test_previsao_proximos_dias_sem_previsao(db_session, empresa):
    vazio = ds.previsao_proximos_dias(db_session, empresa.id)
    assert (vazio.quantidade_prevista, vazio.itens_com_previsao, vazio.base) == (0.0, 0, None)
