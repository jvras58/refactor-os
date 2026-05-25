"""Solução INCORRETA — defeito: PATTERN não aplicado (dependência continua hardcoded)."""

import smtplib


class WelcomeEmailService:
    def __init__(self) -> None:
        # BUG: alega aplicar Dependency Injection, mas o SMTP segue criado dentro da classe.
        self.smtp = smtplib.SMTP("smtp.example.com", 587)
        self.smtp.starttls()
        self.smtp.login("user", "pass")

    def send_welcome(self, user_email: str, name: str) -> None:
        body = f"Hello {name}, welcome!"
        self.smtp.sendmail("noreply@example.com", user_email, body)


def register(user_email: str, name: str) -> None:
    service = WelcomeEmailService()
    service.send_welcome(user_email, name)
