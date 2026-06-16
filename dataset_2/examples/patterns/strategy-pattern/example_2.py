"""Ordenacao de uma lista de produtos por criterio escolhido pelo usuario."""


class CatalogoService:
    def ordenar(self, produtos: list[dict], criterio: str) -> list[dict]:
        if criterio == "nome":
            return sorted(produtos, key=lambda p: p["nome"])
        elif criterio == "preco":
            return sorted(produtos, key=lambda p: p["preco"])
        elif criterio == "data_cadastro":
            return sorted(produtos, key=lambda p: p["data_cadastro"])
        elif criterio == "mais_vendidos":
            return sorted(produtos, key=lambda p: p["vendas"], reverse=True)
        else:
            raise ValueError(f"criterio de ordenacao desconhecido: {criterio}")


class VitrineController:
    def __init__(self):
        self._catalogo = CatalogoService()

    def montar_vitrine(self, produtos: list[dict], criterio_usuario: str) -> list[dict]:
        produtos_ordenados = self._catalogo.ordenar(produtos, criterio_usuario)
        return produtos_ordenados[:20]
