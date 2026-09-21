"""Testes do validador de CNPJ (novo utilitário em app/core/validadores.py)."""

import pytest

from app.core.validadores import cnpj_valido

CNPJ_VALIDO = "11.222.333/0001-81"
CNPJ_VALIDO_2 = "11.444.777/0001-61"


@pytest.mark.parametrize(
    "cnpj",
    [CNPJ_VALIDO, CNPJ_VALIDO_2],
)
def test_cnpj_valido_aceita_cnpjs_reais(cnpj: str) -> None:
    assert cnpj_valido(cnpj) is True


@pytest.mark.parametrize(
    "cnpj",
    [
        "00.000.000/0000-00",  # todos os dígitos iguais
        "11.222.333/0001-00",  # dígitos verificadores errados
        "11.222.333/0001",  # tamanho incompleto
        "abc",
    ],
)
def test_cnpj_valido_rejeita_cnpjs_invalidos(cnpj: str) -> None:
    assert cnpj_valido(cnpj) is False


EMPRESA_PAYLOAD = {
    "nome": "Hospital Novo CNPJ",
    "email_responsavel": "responsavel@hospitalnovocnpj.com",
    "nome_responsavel": "Responsável Novo",
    "endereco": "Rua Nova, 123",
    "cidade": "Joinville",
    "uf": "SC",
}


def test_criar_empresa_com_cnpj_invalido_da_422(client, token_super_admin):
    payload = {**EMPRESA_PAYLOAD, "cnpj": "00.000.000/0000-00"}

    resposta = client.post(
        "/empresas/criar/empresa",
        json=payload,
        headers={"Authorization": f"Bearer {token_super_admin}"},
    )

    assert resposta.status_code == 422


def test_criar_empresa_com_cnpj_valido_e_aceita(client, token_super_admin):
    payload = {**EMPRESA_PAYLOAD, "cnpj": CNPJ_VALIDO}

    resposta = client.post(
        "/empresas/criar/empresa",
        json=payload,
        headers={"Authorization": f"Bearer {token_super_admin}"},
    )

    assert resposta.status_code == 201
    assert resposta.json()["cnpj"] == CNPJ_VALIDO


def test_criar_empresa_sem_cnpj_e_aceita(client, token_super_admin):
    resposta = client.post(
        "/empresas/criar/empresa",
        json=EMPRESA_PAYLOAD,
        headers={"Authorization": f"Bearer {token_super_admin}"},
    )

    assert resposta.status_code == 201
    assert resposta.json()["cnpj"] is None