"""Bad smell: Tight Coupling — esperado: Dependency Injection."""

import smtplib


class WelcomeEmailService:
    def __init__(self):
        # dependência hardcoded — impossível mockar / trocar
        self.smtp = smtplib.SMTP("smtp.example.com", 587)
        self.smtp.starttls()
        self.smtp.login("user", "pass")

    def send_welcome(self, user_email: str, name: str) -> None:
        body = f"Hello {name}, welcome!"
        self.smtp.sendmail("noreply@example.com", user_email, body)


def register(user_email: str, name: str) -> None:
    service = WelcomeEmailService()
    service.send_welcome(user_email, name)
