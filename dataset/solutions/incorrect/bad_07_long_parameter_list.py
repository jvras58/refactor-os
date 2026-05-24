"""Solução INCORRETA — defeito: IMPORT externo desnecessário (dependência de terceiros)."""

import requests  # BUG: biblioteca de terceiros sem necessidade para o pattern
from pydantic import BaseModel  # BUG: dependência externa adicionada sem justificativa


class HttpRequest(BaseModel):
    method: str
    url: str
    headers: dict
    query: dict
    body: bytes
    timeout: float
    retries: int
    verify_ssl: bool
    proxy: str


class HttpClient:
    def request(self, spec: HttpRequest) -> dict:
        _ = requests  # uso simbólico para "justificar" o import
        return spec.model_dump()
