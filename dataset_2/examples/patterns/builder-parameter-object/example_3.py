"""Montagem de requisicao HTTP configuravel."""


def montar_requisicao_http(url, metodo, headers, body, timeout,
                            retries, auth_token, verify_ssl, proxy, allow_redirects):
    return {
        "url": url, "metodo": metodo, "headers": {**headers, "Authorization": auth_token},
        "body": body, "timeout": timeout, "retries": retries,
        "verify_ssl": verify_ssl, "proxy": proxy, "allow_redirects": allow_redirects,
    }


# chamada — 10 posicoes, qualquer troca de ordem entre bool/str passa despercebida
montar_requisicao_http("https://api.example.com", "POST", {}, {"a": 1}, 30, 3, "Bearer xyz", True, None, False)
