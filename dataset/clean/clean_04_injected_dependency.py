"""Código limpo: dependência injetada via construtor (DI já aplicado). Nenhum smell esperado."""

from collections.abc import Callable


class WelcomeEmailService:
    def __init__(self, send: Callable[[str, str], None]) -> None:
        self._send = send

    def send_welcome(self, user_email: str, name: str) -> None:
        self._send(user_email, f"Hello {name}, welcome!")
