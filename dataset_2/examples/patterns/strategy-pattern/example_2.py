"""Recorte de imagem de acordo com o tipo de arquivo enviado."""


class RecortadorImagem:
    def recortar(self, tipo_arquivo: str, imagem, area: dict):
        if tipo_arquivo == "gif":
            return self._recortar_gif_animado(imagem, area)
        else:
            return self._recortar_imagem_estatica(imagem, area)

    def _recortar_gif_animado(self, imagem, area: dict):
        x, y, largura, altura = area["x"], area["y"], area["largura"], area["altura"]
        quadros_recortados = [
            quadro.crop((x, y, x + largura, y + altura)) for quadro in imagem.quadros
        ]
        return self._remontar_gif(quadros_recortados, imagem.duracao_quadro)

    def _recortar_imagem_estatica(self, imagem, area: dict):
        x, y, largura, altura = area["x"], area["y"], area["largura"], area["altura"]
        return imagem.crop((x, y, x + largura, y + altura))

    def _remontar_gif(self, quadros, duracao_quadro): ...


class EditorFotos:
    def __init__(self):
        self._recortador = RecortadorImagem()

    def aplicar_recorte_usuario(self, imagem, tipo_arquivo, area_selecionada: dict):
        return self._recortador.recortar(tipo_arquivo, imagem, area_selecionada)
