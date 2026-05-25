"""Código limpo: funções puras pequenas. Nenhum smell esperado."""


def normalize(text: str) -> str:
    return text.strip().lower()


def slugify(text: str) -> str:
    return normalize(text).replace(" ", "-")


def truncate(text: str, limit: int = 80) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"
