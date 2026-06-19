"""Email sending via Brevo transactional API."""

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_BREVO_URL = "https://api.brevo.com/v3/smtp/email"
_SENDER = {"name": "Atlas · Healz", "email": "atlas@healz.com.br"}


async def _send(to_email: str, subject: str, html: str) -> bool:
    if not settings.BREVO_API_KEY:
        logger.warning("BREVO_API_KEY não configurada — email não enviado para %s", to_email)
        return False

    payload = {
        "sender": _SENDER,
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                _BREVO_URL,
                json=payload,
                headers={"api-key": settings.BREVO_API_KEY, "Content-Type": "application/json"},
            )
            resp.raise_for_status()
        logger.info("Email enviado para %s (assunto: %s)", to_email, subject)
        return True
    except Exception as exc:
        logger.error("Falha ao enviar email para %s: %s", to_email, exc)
        return False


async def send_invite_email(to_email: str, invite_url: str, invited_by_name: str) -> bool:
    subject = "Você foi convidado para o Atlas · Healz"
    html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<body style="font-family: sans-serif; background: #f5f5f5; margin: 0; padding: 32px;">
  <div style="max-width: 520px; margin: 0 auto; background: #fff; border-radius: 12px; padding: 40px; border: 1px solid #e5e7eb;">
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 32px;">
      <span style="font-size: 22px; font-weight: 700; color: #111;">healz</span>
      <span style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.2em; color: #9ca3af; margin-top: 4px;">Atlas</span>
    </div>
    <h2 style="margin: 0 0 16px; color: #111; font-size: 20px;">Você foi convidado!</h2>
    <p style="color: #6b7280; margin: 0 0 24px; line-height: 1.6;">
      <strong style="color: #111;">{invited_by_name}</strong> convidou você para acessar o <strong>Atlas</strong>,
      a plataforma de inteligência da Healz.
    </p>
    <a href="{invite_url}"
       style="display: inline-block; background: #0ea5e9; color: #fff; text-decoration: none;
              padding: 12px 28px; border-radius: 8px; font-weight: 600; font-size: 14px;">
      Criar minha conta
    </a>
    <p style="color: #9ca3af; font-size: 12px; margin: 24px 0 0;">
      Este link expira em <strong>72 horas</strong>. Se você não esperava esse convite, pode ignorar este email.
    </p>
  </div>
</body>
</html>
"""
    return await _send(to_email, subject, html)


async def send_password_reset_email(to_email: str, reset_url: str) -> bool:
    subject = "Redefinição de senha — Atlas · Healz"
    html = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<body style="font-family: sans-serif; background: #f5f5f5; margin: 0; padding: 32px;">
  <div style="max-width: 520px; margin: 0 auto; background: #fff; border-radius: 12px; padding: 40px; border: 1px solid #e5e7eb;">
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 32px;">
      <span style="font-size: 22px; font-weight: 700; color: #111;">healz</span>
      <span style="font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.2em; color: #9ca3af; margin-top: 4px;">Atlas</span>
    </div>
    <h2 style="margin: 0 0 16px; color: #111; font-size: 20px;">Redefinição de senha</h2>
    <p style="color: #6b7280; margin: 0 0 24px; line-height: 1.6;">
      Recebemos uma solicitação de redefinição de senha para a conta associada a este email no Atlas.
    </p>
    <a href="{reset_url}"
       style="display: inline-block; background: #0ea5e9; color: #fff; text-decoration: none;
              padding: 12px 28px; border-radius: 8px; font-weight: 600; font-size: 14px;">
      Redefinir minha senha
    </a>
    <p style="color: #9ca3af; font-size: 12px; margin: 24px 0 0;">
      Este link expira em <strong>1 hora</strong>. Se você não solicitou isso, pode ignorar este email com segurança.
    </p>
  </div>
</body>
</html>
"""
    return await _send(to_email, subject, html)
