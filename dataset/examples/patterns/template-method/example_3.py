"""Publicacao de conteudos digitais em uma plataforma de aprendizagem."""


class PublicadorVideo:
    def publicar(self, arquivo):
        if not validar_arquivo(arquivo):
            raise ValueError("arquivo invalido")
        if arquivo.tamanho_mb > 2048:
            raise ValueError("video excede o tamanho maximo permitido")

        versao_processada = converter_video_para_streaming(arquivo)
        miniatura = gerar_miniatura_video(versao_processada)

        url_armazenamento = armazenar_arquivo(versao_processada)
        publicar_no_ambiente(url_armazenamento, miniatura)
        notificar_usuarios_novo_conteudo(arquivo.titulo)
        return {"url": url_armazenamento, "miniatura": miniatura}


class PublicadorDocumento:
    def publicar(self, arquivo):
        if not validar_arquivo(arquivo):
            raise ValueError("arquivo invalido")
        if arquivo.tamanho_mb > 2048:
            raise ValueError("documento excede o tamanho maximo permitido")

        versao_processada = converter_documento_para_pdf(arquivo)
        miniatura = gerar_preview_primeira_pagina(versao_processada)

        url_armazenamento = armazenar_arquivo(versao_processada)
        publicar_no_ambiente(url_armazenamento, miniatura)
        notificar_usuarios_novo_conteudo(arquivo.titulo)
        return {"url": url_armazenamento, "miniatura": miniatura}


def validar_arquivo(arquivo): ...
def converter_video_para_streaming(arquivo): ...
def gerar_miniatura_video(arquivo): ...
def converter_documento_para_pdf(arquivo): ...
def gerar_preview_primeira_pagina(arquivo): ...
def armazenar_arquivo(arquivo): ...
def publicar_no_ambiente(url, miniatura): ...
def notificar_usuarios_novo_conteudo(titulo): ...
