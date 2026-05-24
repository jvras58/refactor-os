"""Bad smell: Long Parameter List — esperado: Builder/Parameter Object."""


class HttpClient:
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
        return {
            "method": method,
            "url": url,
            "headers": headers,
            "query": query,
            "body": body,
            "timeout": timeout,
            "retries": retries,
            "verify_ssl": verify_ssl,
            "proxy": proxy,
        }
