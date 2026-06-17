"""Integracao com gateway de pagamento externo."""

from typing import Protocol


class GatewayPagamento(Protocol):
    def autorizar(self, valor: float, token: str) -> dict: ...
    def capturar(self, autorizacao_id: str) -> dict: ...
    def estornar(self, captura_id: str) -> dict: ...


class GatewayStripeAdapter:
    def __init__(self, api_key: str):
        self._api_key = api_key

    def autorizar(self, valor, token):
        return {"id": "auth_123", "status": "autorizado"}

    def capturar(self, autorizacao_id):
        return {"id": "cap_123", "status": "capturado"}

    def estornar(self, captura_id):
        return {"id": "ref_123", "status": "estornado"}


class RegistroTransacoes:
    def __init__(self):
        self._transacoes: list[dict] = []

    def registrar(self, evento: dict) -> None:
        self._transacoes.append(evento)

    def historico(self) -> list[dict]:
        return list(self._transacoes)


class ServicoCobranca:
    def __init__(self, gateway: GatewayPagamento, registro: RegistroTransacoes):
        self._gateway = gateway
        self._registro = registro

    def cobrar(self, valor: float, token: str) -> dict:
        autorizacao = self._gateway.autorizar(valor, token)
        if autorizacao["status"] != "autorizado":
            self._registro.registrar({"evento": "autorizacao_falhou", "valor": valor})
            return autorizacao

        captura = self._gateway.capturar(autorizacao["id"])
        self._registro.registrar({"evento": "cobranca_concluida", "valor": valor})
        return captura

    def estornar(self, captura_id: str) -> dict:
        resultado = self._gateway.estornar(captura_id)
        self._registro.registrar({"evento": "estorno", "captura_id": captura_id})
        return resultado
