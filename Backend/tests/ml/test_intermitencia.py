"""Testes da análise de intermitência (SBC)."""

from datetime import date, timedelta

from app.models.consumo import Consumo
from app.models.importacoes import Importacao
from app.services.ml import intermitencia as it
from app.services.ml.intermitencia import Intermitencia


# --------------------------------------------------------------------------- #
# Funções puras
# --------------------------------------------------------------------------- #
def test_classificar_sbc_quadrantes():
    assert it.classificar_sbc(1.0, 0.2) == "suave"
    assert it.classificar_sbc(3.0, 0.2) == "intermitente"
    assert it.classificar_sbc(1.0, 1.0) == "erratico"
    assert it.classificar_sbc(3.0, 1.0) == "lumpy"


def test_metricas_demanda_regular_constante():
    adi, cv2, n = it.calcular_metricas([10, 10, 10, 10, 10])
    assert adi == 1.0
    assert cv2 == 0.0
    assert n == 5


def test_metricas_demanda_esparsa_adi():
    # 10 dias, demanda em 2 deles -> ADI = 10 / 2 = 5
    serie = [0, 0, 0, 0, 8, 0, 0, 0, 0, 8]
    adi, cv2, n = it.calcular_metricas(serie)
    assert n == 2
    assert adi == 5.0


def test_metricas_sem_demanda_retorna_none():
    assert it.calcular_metricas([0, 0, 0]) == (None, None, 0)


def test_analisar_item_esparso_e_inadequado_ao_diario():
    por_dia = {date(2024, 1, 1): 5.0, date(2024, 1, 11): 5.0}  # 2 demandas em 11 dias
    r = it.analisar_item(1, por_dia, date(2024, 1, 1), date(2024, 1, 11))
    assert r.dias_totais == 11
    assert r.dias_com_demanda == 2
    assert r.classe in ("intermitente", "lumpy")
    assert r.adequado_diario is False


def test_resumir_conta_classes_e_percentual():
    res = [
        Intermitencia(1, 30, 30, 1.0, 1.0, 0.0, "suave", True),
        Intermitencia(2, 30, 3, 0.1, 10.0, 0.0, "intermitente", False),
    ]
    resumo = it.resumir(res)
    assert resumo["total_itens"] == 2
    assert resumo["por_classe"]["suave"] == 1
    assert resumo["percentual_adequado_ao_diario"] == 50.0


# --------------------------------------------------------------------------- #
# Carga a partir do banco + rota
# --------------------------------------------------------------------------- #
def _importacao(db, empresa, usuario) -> Importacao:
    imp = Importacao(
        empresa_id=empresa.id, usuario_id=usuario.id,
        nome_arquivo="x.csv", tipo="csv", status="concluido",
    )
    db.add(imp)
    db.flush()
    return imp


def test_analisar_empresa_demanda_densa_e_suave(db_session, empresa, usuario_admin, item):
    imp = _importacao(db_session, empresa, usuario_admin)
    for i in range(10):  # consumo todo dia por 10 dias
        db_session.add(Consumo(
            empresa_id=empresa.id, importacao_id=imp.id, item_id=item.id,
            data=date(2024, 1, 1) + timedelta(days=i),
            quantidade=10, valor=100, local_estoque="Central",
        ))
    db_session.commit()

    resultados = it.analisar_empresa(db_session, empresa.id)
    assert len(resultados) == 1
    assert resultados[0].item_id == item.id
    assert resultados[0].adequado_diario is True  # ADI=1 -> suave


def test_rota_analise_intermitencia_sem_dados(client, token_admin, empresa):
    resposta = client.get(
        "/previsoes/analise-intermitencia",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["resumo"]["total_itens"] == 0
    assert corpo["itens"] == []
