"""Abertura de conexao configuravel com banco de dados."""


def criar_conexao_banco(host, porta, usuario, senha, banco,
                         ssl=True, timeout=30, pool_size=5,
                         charset="utf8", autocommit=False):
    return {
        "host": host, "porta": porta, "usuario": usuario, "banco": banco,
        "ssl": ssl, "timeout": timeout, "pool_size": pool_size,
        "charset": charset, "autocommit": autocommit,
    }


# chamada — dificil saber, so olhando, o que cada posicao representa
criar_conexao_banco("db.internal", 5432, "app", "senha", "producao", True, 60, 10, "utf8", False)
