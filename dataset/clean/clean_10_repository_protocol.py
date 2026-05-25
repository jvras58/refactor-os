"""Código limpo: repositório abstraído por Protocol + injeção. Nenhum smell esperado."""

from typing import Protocol


class UserRepository(Protocol):
    def get(self, user_id: int) -> dict | None: ...


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def display_name(self, user_id: int) -> str:
        user = self._repository.get(user_id)
        return user["name"] if user else "anonymous"
