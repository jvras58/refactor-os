"""Processamento de pagamento por metodo escolhido pelo cliente."""


class ProcessadorPagamento:
    def processar(self, metodo: str, valor: float, parcelas: int = 1) -> dict:
        if metodo == "credito":
            taxa = 0.0399 * parcelas
            valor_final = valor * (1 + taxa)
            return {"status": "aprovado", "valor_final": valor_final, "metodo": metodo}
        elif metodo == "debito":
            if parcelas > 1:
                raise ValueError("debito nao permite parcelamento")
            return {"status": "aprovado", "valor_final": valor, "metodo": metodo}
        elif metodo == "pix":
            valor_final = valor * 0.98
            return {"status": "aprovado", "valor_final": valor_final, "metodo": metodo}
        elif metodo == "boleto":
            valor_final = valor + 2.50
            return {"status": "pendente", "valor_final": valor_final, "metodo": metodo}
        elif metodo == "dinheiro":
            return {"status": "aprovado", "valor_final": valor, "metodo": metodo}
        else:
            raise ValueError(f"metodo de pagamento desconhecido: {metodo}")


class Checkout:
    def __init__(self):
        self._processador = ProcessadorPagamento()

    def finalizar_compra(self, carrinho: dict, metodo: str, parcelas: int = 1) -> dict:
        valor = carrinho["total"]
        resultado = self._processador.processar(metodo, valor, parcelas)
        return {"carrinho": carrinho["id"], **resultado}
