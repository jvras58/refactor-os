"""Criacao de pedido com dados de cliente, produto e endereco de entrega."""


def criar_pedido(cliente_id, produto_id, quantidade, preco_unitario,
                  desconto, frete, endereco, cidade, estado, cep, observacao=None):
    total = (preco_unitario * quantidade - desconto) + frete
    return {
        "cliente_id": cliente_id,
        "produto_id": produto_id,
        "quantidade": quantidade,
        "total": total,
        "endereco": f"{endereco}, {cidade}/{estado} - {cep}",
        "observacao": observacao,
    }


# chamada — facil errar a ordem de cidade/estado, ambos str
criar_pedido(42, 7, 2, 99.90, 10.0, 15.0, "Rua A", "SP", "SP", "01000-000")
