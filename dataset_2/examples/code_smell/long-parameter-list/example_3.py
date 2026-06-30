"""Geracao de relatorio com opcoes de conteudo, formato e envio por email."""


def gerar_relatorio(titulo, autor, data_inicio, data_fim, formato,
                     incluir_graficos, incluir_tabela, destinatario_email, assunto_email):
    conteudo = f"{titulo} ({data_inicio} a {data_fim}) por {autor}"
    if incluir_graficos:
        conteudo += "\n[graficos]"
    if incluir_tabela:
        conteudo += "\n[tabela]"

    arquivo = _exportar(conteudo, formato)

    if destinatario_email:
        _enviar_email(destinatario_email, assunto_email, arquivo)

    return arquivo


def _exportar(conteudo: str, formato: str) -> bytes: ...
def _enviar_email(destinatario: str, assunto: str, anexo: bytes) -> None: ...


# chamada — 9 argumentos posicionais, sem nenhuma pista do que e o que
gerar_relatorio("Vendas Q1", "Joao", "2026-01-01", "2026-03-31", "pdf", True, True, "diretoria@empresa.com", "Relatorio Q1")
