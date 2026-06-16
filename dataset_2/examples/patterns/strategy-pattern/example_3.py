"""Validacao de senha com diferentes niveis de exigencia."""


def validar_senha(senha: str, forca: str) -> bool:
    if forca == "fraca":
        return len(senha) >= 4
    elif forca == "media":
        return len(senha) >= 8 and any(c.isdigit() for c in senha)
    elif forca == "forte":
        return (
            len(senha) >= 12
            and any(c.isdigit() for c in senha)
            and any(c.isupper() for c in senha)
            and any(c in "!@#$%^&*" for c in senha)
        )
    else:
        raise ValueError(f"nivel de forca desconhecido: {forca}")
