"""Fechamento de pedido no checkout, envolvendo estoque, imposto, pagamento e nota fiscal."""


def fechar_pedido_no_checkout(produto_id, quantidade, valor, estado, dados_pagamento):
    estoque = EstoqueSubsistema()
    imposto = ImpostoSubsistema()
    pagamento = PagamentoSubsistema()
    nota = NotaFiscalSubsistema()

    if not estoque.verificar_disponibilidade(produto_id, quantidade):
        raise RuntimeError("sem estoque")
    estoque.reservar(produto_id, quantidade)

    valor_imposto = imposto.calcular(valor, estado)
    valor_total = valor + valor_imposto

    resultado_pagamento = pagamento.cobrar(dados_pagamento, valor_total)
    if resultado_pagamento["status"] != "aprovado":
        estoque.liberar_reserva(produto_id, quantidade)
        raise RuntimeError("pagamento recusado")

    estoque.confirmar_baixa(produto_id, quantidade)
    nota.emitir(produto_id, quantidade, valor_total)

    return {"status": "concluido", "valor_total": valor_total}


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
