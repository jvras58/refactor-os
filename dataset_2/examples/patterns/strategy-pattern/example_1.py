"""Normalizacao de imagens recebidas em diferentes formatos no upload."""

import base64


class ProcessadorImagemUpload:
    def processar(self, tipo_origem: str, conteudo) -> bytes:
        if tipo_origem == "base64":
            return base64.b64decode(conteudo)
        elif tipo_origem == "arquivo":
            return conteudo.read()
        elif tipo_origem == "url":
            return self._baixar_de_url(conteudo)
        elif tipo_origem == "bytes":
            return conteudo
        else:
            raise ValueError(f"origem de imagem desconhecida: {tipo_origem}")

    def _baixar_de_url(self, url: str) -> bytes: ...


class ControladorUpload:
    def __init__(self):
        self._processador = ProcessadorImagemUpload()

    def receber_imagem(self, tipo_origem: str, conteudo) -> dict:
        dados_imagem = self._processador.processar(tipo_origem, conteudo)
        return {"tamanho_bytes": len(dados_imagem), "origem": tipo_origem}
