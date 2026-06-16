"""Geracao, armazenamento e distribuicao de relatorios."""


class GerenciadorRelatorio:
    def __init__(self):
        self.relatorios_gerados = []

    def gerar_e_distribuir(self, dados, destinatarios):
        pdf = self.gerar_pdf(dados)
        url = self.upload_storage(pdf)
        for destinatario in destinatarios:
            self.enviar_email(destinatario, url)
        self.relatorios_gerados.append(url)
        return url

    def gerar_pdf(self, dados): ...
    def upload_storage(self, pdf_bytes): ...
    def enviar_email(self, destinatario, url): ...
    def listar_relatorios_gerados(self): ...
    def excluir_relatorio_antigo(self, url): ...
