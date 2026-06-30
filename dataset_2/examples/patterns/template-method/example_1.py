"""Processamento de pedidos por canal de venda (online e loja fisica)."""


class ProcessadorPedidoOnline:
    def processar(self, pedido):
        if not pedido.get("endereco_entrega"):
            raise ValueError("pedido online exige endereco de entrega")
        self._reservar_estoque(pedido)
        self._cobrar_cartao(pedido)
        self._confirmar(pedido)
        return {"status": "confirmado", "canal": "online"}

    def _reservar_estoque(self, pedido): ...
    def _cobrar_cartao(self, pedido): ...
    def _confirmar(self, pedido): ...


class ProcessadorPedidoLoja:
    def processar(self, pedido):
        if not pedido.get("caixa_id"):
            raise ValueError("pedido de loja exige identificacao do caixa")
        self._reservar_estoque(pedido)
        self._cobrar_dinheiro_ou_debito(pedido)
        self._confirmar(pedido)
        return {"status": "confirmado", "canal": "loja"}

    def _reservar_estoque(self, pedido): ...
    def _cobrar_dinheiro_ou_debito(self, pedido): ...
    def _confirmar(self, pedido): ...
