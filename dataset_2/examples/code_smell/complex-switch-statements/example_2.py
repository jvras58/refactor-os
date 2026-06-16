"""Processamento de pagamento por metodo escolhido pelo cliente."""


def processar_pagamento(metodo: str, valor: float, parcelas: int = 1) -> dict:
    if metodo == "credito":
        taxa = 0.0399 * parcelas
        valor_final = valor * (1 + taxa)
        return {"status": "aprovado", "valor_final": valor_final, "metodo": metodo}
    elif metodo == "debito":
        if parcelas > 1:
            raise ValueError("debito nao permite parcelamento")
        return {"status": "aprovado", "valor_final": valor, "metodo": metodo}
    elif metodo == "pix":
        valor_final = valor * 0.98  # desconto de 2%
        return {"status": "aprovado", "valor_final": valor_final, "metodo": metodo}
    elif metodo == "boleto":
        valor_final = valor + 2.50  # taxa fixa de emissao
        return {"status": "pendente", "valor_final": valor_final, "metodo": metodo}
    elif metodo == "dinheiro":
        return {"status": "aprovado", "valor_final": valor, "metodo": metodo}
    else:
        raise ValueError(f"metodo de pagamento desconhecido: {metodo}")
