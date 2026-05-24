"""Código limpo: switch curto e de baixa complexidade (3 ramos simples). Nenhum smell esperado."""


def http_status_label(code: int) -> str:
    if code < 300:
        return "success"
    if code < 400:
        return "redirect"
    if code < 500:
        return "client_error"
    return "server_error"
