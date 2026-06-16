"""Validacao de cadastro de clientes e de fornecedores."""


def validar_cadastro_cliente(dados: dict) -> list[str]:
    erros = []
    if not dados.get("nome"):
        erros.append("nome e obrigatorio")
    if not dados.get("email") or "@" not in dados["email"]:
        erros.append("email invalido")
    cpf = dados.get("cpf", "")
    if len(cpf.replace(".", "").replace("-", "")) != 11:
        erros.append("cpf invalido")
    if not dados.get("telefone"):
        erros.append("telefone e obrigatorio")
    return erros


def validar_cadastro_fornecedor(dados: dict) -> list[str]:
    erros = []
    if not dados.get("nome"):
        erros.append("nome e obrigatorio")
    if not dados.get("email") or "@" not in dados["email"]:
        erros.append("email invalido")
    cnpj = dados.get("cnpj", "")
    if len(cnpj.replace(".", "").replace("-", "").replace("/", "")) != 14:
        erros.append("cnpj invalido")
    if not dados.get("telefone"):
        erros.append("telefone e obrigatorio")
    return erros
