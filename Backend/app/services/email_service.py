import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

LOGO_PATH = Path(__file__).resolve().parent.parent.parent / "imagens" / "MedStockAi-logo.png"


def enviar_email(destinatario: str, assunto: str, texto: str, html: str) -> None:
    mensagem = EmailMessage()
    mensagem["Subject"] = assunto
    mensagem["From"] = settings.EMAIL_REMETENTE
    mensagem["To"] = destinatario
    mensagem.set_content(texto)
    mensagem.add_alternative(html, subtype="html")
    mensagem.get_payload()[1].add_related(
        LOGO_PATH.read_bytes(), maintype="image", subtype="png", cid="logo"
    )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(settings.EMAIL_REMETENTE, settings.SENHA_EMAIL)
        smtp.send_message(mensagem)

    logger.info("E-mail enviado para=%s assunto=%s", destinatario, assunto)


def montar_email_definicao_senha(nome: str, link: str) -> tuple[str, str]:
    texto = (
        f"Olá {nome},\n\n"
        "Seu cadastro foi realizado com sucesso.\n"
        f"Acesse o link abaixo para definir sua senha e acessar o sistema:\n{link}\n\n"
        "Este link tem validade de 48 horas após o envio.\n"
        "Caso não tenha solicitado este cadastro, ignore este e-mail."
    )

    html = f"""\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 20px 0; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
  <table role="presentation" width="100%" border="0" cellspacing="0" cellpadding="0">
    <tr>
      <td align="center">
        <div style="max-width: 460px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; padding: 36px 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03); border: 1px solid #e2e8f0; text-align: left;">
          
          <!-- Logo -->
          <div style="text-align: center; margin-bottom: 28px;">
            <img src="cid:logo" alt="MedStock AI" style="max-width: 170px; height: auto;">
          </div>
          
          <!-- Corpo da Mensagem -->
          <h2 style="color: #0f172a; font-size: 18px; font-weight: 600; margin: 0 0 16px 0;">
            Olá, {nome}!
          </h2>
          
          <p style="color: #334155; font-size: 15px; line-height: 1.6; margin: 0 0 12px 0;">
            Seu cadastro no <strong>MedStock AI</strong> foi realizado com sucesso.
          </p>
          
          <p style="color: #334155; font-size: 15px; line-height: 1.6; margin: 0 0 28px 0;">
            Clique no botão abaixo para criar a sua senha e começar a acessar o sistema:
          </p>
          
          <!-- Botão CTA -->
          <div style="text-align: center; margin-bottom: 32px;">
            <a href="{link}"
               style="background-color: #0f766e; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 15px; display: inline-block; box-shadow: 0 2px 4px rgba(15, 118, 110, 0.2);">
               Definir senha e acessar
            </a>
          </div>
          
          <!-- Divisor -->
          <hr style="border: none; border-top: 1px solid #f1f5f9; margin: 24px 0;">
          
          <!-- Rodapé de Aviso -->
          <p style="font-size: 12px; color: #64748b; line-height: 1.5; margin: 0 0 8px 0;">
            ⏳ <strong>Atenção:</strong> Este link é válido por <strong>48 horas</strong>.
          </p>
          <p style="font-size: 12px; color: #94a3b8; line-height: 1.5; margin: 0;">
            Se você não solicitou este cadastro, pode ignorar este e-mail com segurança.
          </p>
          
        </div>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    return texto, html