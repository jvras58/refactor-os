"""Montagem de requisicao HTTP configuravel."""


class ClienteHttp:
    def montar_requisicao(self, url, metodo, headers, body, timeout,
                           retries, auth_token, verify_ssl, proxy, allow_redirects):
        return {
            "url": url, "metodo": metodo, "headers": {**headers, "Authorization": auth_token},
            "body": body, "timeout": timeout, "retries": retries,
            "verify_ssl": verify_ssl, "proxy": proxy, "allow_redirects": allow_redirects,
        }

    def enviar(self, requisicao: dict) -> dict: ...


class IntegradorExterno:
    def __init__(self):
        self._http = ClienteHttp()

    def sincronizar_pedido(self, pedido: dict, token: str) -> dict:
        requisicao = self._http.montar_requisicao(
            "https://parceiro.example.com/pedidos", "POST", {}, pedido,
            30, 3, token, True, None, False,
        )
        return self._http.enviar(requisicao)
