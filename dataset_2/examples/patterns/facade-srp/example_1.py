"""Fechamento de pedido no checkout, envolvendo estoque, imposto, pagamento e nota fiscal."""


class EstoqueSubsistema:
    def verificar_disponibilidade(self, produto_id, qtd): ...
    def reservar(self, produto_id, qtd): ...
    def liberar_reserva(self, produto_id, qtd): ...
    def confirmar_baixa(self, produto_id, qtd): ...


class ImpostoSubsistema:
    def calcular(self, valor, estado): ...


class PagamentoSubsistema:
    def cobrar(self, dados, valor): ...


class NotaFiscalSubsistema:
    def emitir(self, produto_id, quantidade, valor_total): ...


class LojaController:
    def __init__(self):
        self._estoque = EstoqueSubsistema()
        self._imposto = ImpostoSubsistema()
        self._pagamento = PagamentoSubsistema()
        self._nota = NotaFiscalSubsistema()

    def receber_pedido_do_carrinho(self, request: dict) -> dict:
        produto_id = request["produto_id"]
        quantidade = request["quantidade"]
        valor = request["valor"]
        estado = request["estado"]

        if not self._estoque.verificar_disponibilidade(produto_id, quantidade):
            raise RuntimeError("sem estoque")
        self._estoque.reservar(produto_id, quantidade)

        valor_imposto = self._imposto.calcular(valor, estado)
        valor_total = valor + valor_imposto

        resultado_pagamento = self._pagamento.cobrar(request["dados_pagamento"], valor_total)
        if resultado_pagamento["status"] != "aprovado":
            self._estoque.liberar_reserva(produto_id, quantidade)
            raise RuntimeError("pagamento recusado")

        self._estoque.confirmar_baixa(produto_id, quantidade)
        self._nota.emitir(produto_id, quantidade, valor_total)

        return {"status": "concluido", "valor_total": valor_total}
