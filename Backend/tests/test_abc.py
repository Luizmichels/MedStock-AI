"""Testes da classificação ABC por valor acumulado (RN05 / correção D1)."""

from datetime import date

from app.models.classificacao_abc import ClassificacaoABC
from app.models.consumo_tratado import ConsumoTratado
from app.models.itens import Item
from app.services.abc_service import recalcular_abc


def _criar_item(db, empresa, codigo: str) -> Item:
    item = Item(empresa_id=empresa.id, codigo_item=codigo, descricao_item=f"Item {codigo}")
    db.add(item)
    db.flush()
    return item


def _tratado(db, empresa, item, *, valor: float, quantidade: float = 1.0) -> None:
    db.add(
        ConsumoTratado(
            empresa_id=empresa.id,
            item_id=item.id,
            periodo=date(2024, 1, 1),
            quantidade_total=quantidade,
            valor_total=valor,
            local_estoque=None,
        )
    )


def _classes_por_item(db, empresa) -> dict[int, str]:
    linhas = (
        db.query(ClassificacaoABC)
        .filter(ClassificacaoABC.empresa_id == empresa.id)
        .all()
    )
    return {c.item_id: c.classe for c in linhas}


def test_abc_classifica_por_valor_nao_por_quantidade(db_session, empresa):
    # Ranking por VALOR é o inverso do ranking por QUANTIDADE.
    caro = _criar_item(db_session, empresa, "CARO")
    medio = _criar_item(db_session, empresa, "MEDIO")
    barato = _criar_item(db_session, empresa, "BARATO")
    _tratado(db_session, empresa, caro, valor=70, quantidade=10)
    _tratado(db_session, empresa, medio, valor=20, quantidade=20)
    _tratado(db_session, empresa, barato, valor=10, quantidade=70)
    db_session.commit()

    recalcular_abc(db_session, empresa.id)

    classes = _classes_por_item(db_session, empresa)
    # Pelo valor: o item caro é classe A; se agregasse por quantidade seria C.
    assert classes[caro.id] == "A"
    assert classes[barato.id] == "C"


def test_abc_faixas_70_20_10(db_session, empresa):
    a = _criar_item(db_session, empresa, "A70")
    b = _criar_item(db_session, empresa, "B20")
    c = _criar_item(db_session, empresa, "C10")
    _tratado(db_session, empresa, a, valor=70)
    _tratado(db_session, empresa, b, valor=20)
    _tratado(db_session, empresa, c, valor=10)
    db_session.commit()

    recalcular_abc(db_session, empresa.id)

    classes = _classes_por_item(db_session, empresa)
    assert classes[a.id] == "A"
    assert classes[b.id] == "B"
    assert classes[c.id] == "C"


def test_abc_sem_dados_nao_quebra(db_session, empresa):
    recalcular_abc(db_session, empresa.id)
    assert _classes_por_item(db_session, empresa) == {}


def test_abc_recalculo_substitui_classificacao_anterior(db_session, empresa):
    item = _criar_item(db_session, empresa, "UNICO")
    _tratado(db_session, empresa, item, valor=100)
    db_session.commit()

    recalcular_abc(db_session, empresa.id)
    recalcular_abc(db_session, empresa.id)

    linhas = (
        db_session.query(ClassificacaoABC)
        .filter(ClassificacaoABC.empresa_id == empresa.id)
        .all()
    )
    assert len(linhas) == 1


def test_abc_isolado_por_empresa(db_session, empresa, empresa_secundaria):
    item1 = _criar_item(db_session, empresa, "E1")
    item2 = _criar_item(db_session, empresa_secundaria, "E2")
    _tratado(db_session, empresa, item1, valor=100)
    _tratado(db_session, empresa_secundaria, item2, valor=100)
    db_session.commit()

    recalcular_abc(db_session, empresa.id)

    assert item1.id in _classes_por_item(db_session, empresa)
    assert _classes_por_item(db_session, empresa_secundaria) == {}


def test_abc_total_geral_zero_retorna_sem_erro(db_session, empresa):
    item = _criar_item(db_session, empresa, "ZERO")
    _tratado(db_session, empresa, item, valor=0)
    db_session.commit()

    recalcular_abc(db_session, empresa.id)
    assert _classes_por_item(db_session, empresa) == {}


def test_abc_item_unico_recebe_classe_a(db_session, empresa):
    item = _criar_item(db_session, empresa, "SO_EU")
    _tratado(db_session, empresa, item, valor=500)
    db_session.commit()

    recalcular_abc(db_session, empresa.id)
    assert _classes_por_item(db_session, empresa)[item.id] == "A"


# --------------------------------------------------------------------------- #
# Classificação XYZ (RF05)
# --------------------------------------------------------------------------- #
def test_classe_xyz_estavel_e_x():
    from app.services.abc_service import classe_xyz
    assert classe_xyz(0.0) == "X"


def test_classe_xyz_erratico_e_z():
    from app.services.abc_service import classe_xyz
    assert classe_xyz(1.5) == "Z"


def _tratado_periodo(db, empresa, item, periodo, quantidade):
    db.add(ConsumoTratado(
        empresa_id=empresa.id, item_id=item.id, periodo=periodo,
        quantidade_total=quantidade, valor_total=quantidade, local_estoque=None,
    ))


def test_classificar_xyz_serie_constante_e_x(db_session, empresa):
    from datetime import date
    from app.services.abc_service import classificar_xyz
    item = _criar_item(db_session, empresa, "ESTAVEL")
    for mes in (1, 2, 3):
        _tratado_periodo(db_session, empresa, item, date(2024, mes, 1), 100)
    db_session.commit()
    assert classificar_xyz(db_session, empresa.id)[item.id] == "X"


def test_classificar_xyz_serie_erratica_e_z(db_session, empresa):
    from datetime import date
    from app.services.abc_service import classificar_xyz
    item = _criar_item(db_session, empresa, "ERRATICO")
    for mes, qtd in ((1, 1), (2, 100), (3, 1)):
        _tratado_periodo(db_session, empresa, item, date(2024, mes, 1), qtd)
    db_session.commit()
    assert classificar_xyz(db_session, empresa.id)[item.id] == "Z"


def test_matriz_abc_xyz_combina_classes(db_session, empresa):
    from datetime import date
    from app.services.abc_service import matriz_abc_xyz
    item = _criar_item(db_session, empresa, "COMB")
    for mes in (1, 2, 3):
        _tratado_periodo(db_session, empresa, item, date(2024, mes, 1), 100)
    db_session.commit()
    recalcular_abc(db_session, empresa.id)

    matriz = matriz_abc_xyz(db_session, empresa.id)
    assert matriz.get("AX") == 1
