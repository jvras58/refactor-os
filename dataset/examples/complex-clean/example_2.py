"""Geracao de relatorios operacionais com layouts diferentes por area."""

from abc import ABC, abstractmethod


class RelatorioBase(ABC):
    def gerar(self, dados: list[dict]) -> str:
        cabecalho = f"{self._titulo()}\n" + "-" * 20
        linhas = [self._formatar_linha(d) for d in dados]
        rodape = self._rodape(len(linhas))
        return "\n".join([cabecalho, *linhas, rodape])

    @abstractmethod
    def _titulo(self) -> str: ...

    @abstractmethod
    def _formatar_linha(self, dado: dict) -> str: ...

    def _rodape(self, total: int) -> str:
        return f"Total de registros: {total}"


class RelatorioVendas(RelatorioBase):
    def _titulo(self):
        return "Relatorio de Vendas"

    def _formatar_linha(self, dado):
        return f"{dado['produto']}: {dado['quantidade']} unidades"


class RelatorioEstoque(RelatorioBase):
    def _titulo(self):
        return "Relatorio de Estoque"

    def _formatar_linha(self, dado):
        return f"{dado['produto']}: {dado['saldo']} em estoque"


class RepositorioRelatorios:
    def __init__(self):
        self._geradores: dict[str, RelatorioBase] = {
            "vendas": RelatorioVendas(),
            "estoque": RelatorioEstoque(),
        }

    def gerar(self, tipo: str, dados: list[dict]) -> str:
        gerador = self._geradores[tipo]
        return gerador.gerar(dados)

    def gerar_todos(self, dados_por_tipo: dict[str, list[dict]]) -> dict[str, str]:
        return {
            tipo: self.gerar(tipo, dados)
            for tipo, dados in dados_por_tipo.items()
        }
