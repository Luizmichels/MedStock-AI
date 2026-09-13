"""Testes do serviço de e-mail (SMTP mockado)."""

from unittest.mock import MagicMock

from app.services import email_service


def test_montar_email_retorna_texto_e_html():
    texto, html = email_service.montar_email_definicao_senha("Ana", "http://x/definir")
    assert isinstance(texto, str)
    assert isinstance(html, str)


def test_montar_email_inclui_link():
    texto, html = email_service.montar_email_definicao_senha("Ana", "http://x/definir-senha")
    assert "http://x/definir-senha" in texto
    assert "http://x/definir-senha" in html


def test_montar_email_inclui_nome():
    texto, _ = email_service.montar_email_definicao_senha("Ana Paula", "http://x")
    assert "Ana Paula" in texto


def test_enviar_email_usa_smtp(monkeypatch):
    smtp_mock = MagicMock()
    monkeypatch.setattr("app.services.email_service.smtplib.SMTP", smtp_mock)

    email_service.enviar_email("destino@x.com", "Assunto", "texto", "<b>html</b>")

    smtp_mock.assert_called_once()
    instancia = smtp_mock.return_value.__enter__.return_value
    instancia.send_message.assert_called_once()
