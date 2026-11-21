import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService(Protocol):
    """Interface simples para envio de e-mails transacionais, facilitando troca de provedor."""

    def send_password_reset(self, to_email: str, code: str) -> None:
        ...


class ConsoleEmailService:
    """Backend de desenvolvimento: imprime o código de redefinição no terminal."""

    def send_password_reset(self, to_email: str, code: str) -> None:
        print(
            "\n"
            "================ [MAIL_BACKEND=console] ================\n"
            f"Para: {to_email}\n"
            "Assunto: Código de redefinição de senha\n"
            f"Código (6 dígitos): {code}\n"
            "========================================================\n",
            flush=True,
        )


class SmtpEmailService:
    """Backend SMTP (Gmail com senha de app via STARTTLS). Síncrono para rodar em threadpool."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        mail_from: str,
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.mail_from = mail_from or user

    def send_password_reset(self, to_email: str, code: str) -> None:
        if not self.host or not self.user or not self.password:
            logger.error("Configuração SMTP incompleta; e-mail de redefinição não enviado.")
            return

        msg = EmailMessage()
        msg["Subject"] = "Código de redefinição de senha"
        msg["From"] = self.mail_from
        msg["To"] = to_email
        msg.set_content(
            "Você solicitou a redefinição da sua senha.\n\n"
            f"Seu código de verificação é: {code}\n\n"
            "Este código é válido por 15 minutos e possui uso único.\n"
            "Se você não solicitou esta alteração, ignore este e-mail."
        )

        try:
            with smtplib.SMTP(self.host, self.port, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.user, self.password)
                server.send_message(msg)
        except Exception:
            logger.exception("Falha ao enviar e-mail de redefinição via SMTP.")


def get_email_service() -> EmailService:
    backend = settings.MAIL_BACKEND.strip().lower()
    if backend == "smtp":
        return SmtpEmailService(
            host=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            user=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            mail_from=settings.MAIL_FROM,
        )
    return ConsoleEmailService()


def send_password_reset_email(to_email: str, code: str) -> None:
    """Função síncrona (def) segura para uso em FastAPI BackgroundTasks sem bloquear o event loop."""
    service = get_email_service()
    service.send_password_reset(to_email=to_email, code=code)
