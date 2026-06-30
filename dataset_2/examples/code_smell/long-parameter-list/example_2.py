"""Cadastro de usuario com dados pessoais, endereco e credenciais."""


def criar_usuario(nome, email, senha, idade, cidade, estado, pais,
                   telefone=None, cpf=None):
    if idade < 18:
        raise ValueError("usuario deve ser maior de idade")
    return {
        "nome": nome,
        "email": email,
        "senha_hash": _hash(senha),
        "idade": idade,
        "endereco": f"{cidade}/{estado} - {pais}",
        "telefone": telefone,
        "cpf": cpf,
    }


def _hash(valor: str) -> str:
    return f"hash({valor})"


# chamada — 9 posicoes, nenhuma indicacao do que cada uma significa
criar_usuario("Ana Silva", "ana@example.com", "senha123", 30, "Recife", "PE", "BR", "81999990000", "000.000.000-00")
