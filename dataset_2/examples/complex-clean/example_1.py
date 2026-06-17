"""Pipeline de processamento de pedidos: validacao, precificacao e despacho."""

from dataclasses import dataclass


@dataclass
class ItemPedido:
    produto_id: int
    quantidade: int
    preco_unitario: float


@dataclass
class DadosPedido:
    cliente_id: int
    itens: list[ItemPedido]
    cupom: str | None = None


class ValidadorPedido:
    def validar(self, dados: DadosPedido) -> list[str]:
        erros = []
        if not dados.itens:
            erros.append("pedido sem itens")
        for item in dados.itens:
            if item.quantidade <= 0:
                erros.append(f"quantidade invalida para produto {item.produto_id}")
        return erros


class EstrategiaDesconto:
    def aplicar(self, subtotal: float) -> float:
        raise NotImplementedError


class SemDesconto(EstrategiaDesconto):
    def aplicar(self, subtotal):
        return subtotal


class DescontoPercentual(EstrategiaDesconto):
    def __init__(self, percentual: float):
        self._percentual = percentual

    def aplicar(self, subtotal):
        return subtotal * (1 - self._percentual)


class CalculadoraPreco:
    _CUPONS: dict[str, EstrategiaDesconto] = {
        "BEMVINDO10": DescontoPercentual(0.10),
        "BLACKFRIDAY": DescontoPercentual(0.30),
    }

    def calcular(self, dados: DadosPedido) -> float:
        subtotal = sum(item.preco_unitario * item.quantidade for item in dados.itens)
        estrategia = self._CUPONS.get(dados.cupom, SemDesconto())
        return estrategia.aplicar(subtotal)


class DespachanteEstoque:
    def reservar(self, itens: list[ItemPedido]) -> bool:
        return all(self._tem_estoque(item) for item in itens)

    def _tem_estoque(self, item: ItemPedido) -> bool:
        return True


class PedidoOrchestrator:
    def __init__(self):
        self._validador = ValidadorPedido()
        self._precificador = CalculadoraPreco()
        self._estoque = DespachanteEstoque()

    def processar(self, dados: DadosPedido) -> dict:
        erros = self._validador.validar(dados)
        if erros:
            return {"status": "rejeitado", "erros": erros}
        if not self._estoque.reservar(dados.itens):
            return {"status": "sem_estoque"}
        total = self._precificador.calcular(dados)
        return {"status": "aprovado", "total": total}
