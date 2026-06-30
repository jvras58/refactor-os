"""Cobranca de cliente atraves de gateway de pagamento."""


def cobrar_cliente_no_checkout(cartao, valor, cliente_id):
    gateway = GatewayPagamento()

    sessao = gateway.autenticar(api_key="...")
    token_cartao = gateway.tokenizar_cartao(sessao, cartao)

    risco = gateway.checar_antifraude(sessao, cliente_id, valor)
    if risco["score"] > 0.8:
        raise RuntimeError("transacao bloqueada por risco de fraude")

    autorizacao = gateway.autorizar(sessao, token_cartao, valor)
    captura = gateway.capturar(sessao, autorizacao["id"])

    gateway.notificar_webhook(cliente_id, captura["id"])
    return captura


class GatewayPagamento:
    def autenticar(self, api_key): ...
    def tokenizar_cartao(self, sessao, cartao): ...
    def checar_antifraude(self, sessao, cliente_id, valor): ...
    def autorizar(self, sessao, token_cartao, valor): ...
    def capturar(self, sessao, autorizacao_id): ...
    def notificar_webhook(self, cliente_id, captura_id): ...
