"""Geracao de cartao de contato em formato vCard ou em payload para QR Code."""


class CartaoContato:
    def montar_vcard(self, contato: dict) -> str:
        linhas = [
            "BEGIN:VCARD", "VERSION:3.0",
            f"FN:{contato['nome']}", f"TEL:{contato['telefone']}", f"EMAIL:{contato['email']}",
        ]
        if contato.get("empresa"):
            linhas.append(f"ORG:{contato['empresa']}")
        if contato.get("cargo"):
            linhas.append(f"TITLE:{contato['cargo']}")
        linhas.append("END:VCARD")
        return "\n".join(linhas)

    def montar_qrcode_payload(self, contato: dict) -> dict:
        dados = {"nome": contato["nome"], "telefone": contato["telefone"], "email": contato["email"]}
        if contato.get("empresa"):
            dados["empresa"] = contato["empresa"]
        if contato.get("cargo"):
            dados["cargo"] = contato["cargo"]
        return dados
