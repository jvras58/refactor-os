"""Cadastro de usuario com dados pessoais, endereco e credenciais."""


class CadastroService:
    def criar_usuario(self, nome, email, senha, idade, cidade, estado, pais,
                       telefone=None, cpf=None):
        if idade < 18:
            raise ValueError("usuario deve ser maior de idade")
        return {
            "nome": nome,
            "email": email,
            "senha_hash": self._hash(senha),
            "idade": idade,
            "endereco": f"{cidade}/{estado} - {pais}",
            "telefone": telefone,
            "cpf": cpf,
        }

    def _hash(self, valor: str) -> str:
        return f"hash({valor})"


class OnboardingController:
    def __init__(self):
        self._cadastro = CadastroService()

    def receber_formulario(self, dados: dict) -> dict:
        return self._cadastro.criar_usuario(
            dados["nome"], dados["email"], dados["senha"], dados["idade"],
            dados["cidade"], dados["estado"], dados["pais"],
            dados.get("telefone"), dados.get("cpf"),
        )
