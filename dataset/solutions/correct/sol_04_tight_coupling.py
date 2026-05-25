"""Solução CORRETA — Dependency Injection: SMTP injetado, testável (API preservada)."""


class WelcomeEmailService:
    def __init__(self, smtp) -> None:
        # dependência injetada — fácil de substituir por um fake nos testes
        self.smtp = smtp

    def send_welcome(self, user_email: str, name: str) -> None:
        body = f"Hello {name}, welcome!"
        self.smtp.sendmail("noreply@example.com", user_email, body)


def register(user_email: str, name: str, smtp=None) -> None:
    if smtp is None:
        smtp = _build_default_smtp()
    service = WelcomeEmailService(smtp)
    service.send_welcome(user_email, name)


def _build_default_smtp():
    import smtplib

    smtp = smtplib.SMTP("smtp.example.com", 587)
    smtp.starttls()
    smtp.login("user", "pass")
    return smtp
