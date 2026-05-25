"""Código limpo: validador coeso com poucas responsabilidades. Nenhum smell esperado."""


class PasswordPolicy:
    def __init__(self, min_length: int = 8) -> None:
        self.min_length = min_length

    def is_long_enough(self, password: str) -> bool:
        return len(password) >= self.min_length

    def has_digit(self, password: str) -> bool:
        return any(c.isdigit() for c in password)

    def is_valid(self, password: str) -> bool:
        return self.is_long_enough(password) and self.has_digit(password)
