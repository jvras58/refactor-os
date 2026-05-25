"""Solução CORRETA — Parameter Object; método público preservado via wrapper."""

from dataclasses import dataclass


@dataclass
class HttpRequest:
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
    def send(self, request: HttpRequest) -> dict:
        return {
            "method": request.method,
            "url": request.url,
            "headers": request.headers,
            "query": request.query,
            "body": request.body,
            "timeout": request.timeout,
            "retries": request.retries,
            "verify_ssl": request.verify_ssl,
            "proxy": request.proxy,
        }

    def request(
        self,
        method: str,
        url: str,
        headers: dict,
        query: dict,
        body: bytes,
        timeout: float,
        retries: int,
        verify_ssl: bool,
        proxy: str,
    ) -> dict:
        return self.send(
            HttpRequest(method, url, headers, query, body, timeout, retries, verify_ssl, proxy)
        )
