"""Importacao em massa de usuarios para a plataforma, a partir de diferentes origens."""


class ImportadorUsuariosCSV:
    def importar(self, origem):
        dados_brutos = ler_arquivo_csv(origem)
        if not validar_formato_csv(dados_brutos):
            raise ValueError("formato de CSV invalido")

        usuarios = []
        erros = []
        for linha in dados_brutos:
            usuario = {
                "nome": linha["nome"].strip(),
                "email": linha["email"].strip().lower(),
                "documento": normalizar_documento(linha["documento"]),
            }
            if usuario_ja_existe(usuario["email"]):
                erros.append(f"usuario duplicado: {usuario['email']}")
                continue
            criar_ou_atualizar_usuario(usuario)
            usuarios.append(usuario)

        return gerar_relatorio_importacao(usuarios, erros)


class ImportadorUsuariosAPIExterna:
    def importar(self, origem):
        dados_brutos = consultar_api_externa(origem)
        if not validar_resposta_api(dados_brutos):
            raise ValueError("resposta da API em formato invalido")

        usuarios = []
        erros = []
        for registro in dados_brutos:
            usuario = {
                "nome": registro["full_name"].strip(),
                "email": registro["email_address"].strip().lower(),
                "documento": normalizar_documento(registro["document_id"]),
            }
            if usuario_ja_existe(usuario["email"]):
                erros.append(f"usuario duplicado: {usuario['email']}")
                continue
            criar_ou_atualizar_usuario(usuario)
            usuarios.append(usuario)

        return gerar_relatorio_importacao(usuarios, erros)


def ler_arquivo_csv(origem): ...
def validar_formato_csv(dados): ...
def consultar_api_externa(origem): ...
def validar_resposta_api(dados): ...
def normalizar_documento(documento): ...
def usuario_ja_existe(email): ...
def criar_ou_atualizar_usuario(usuario): ...
def gerar_relatorio_importacao(usuarios, erros): ...
