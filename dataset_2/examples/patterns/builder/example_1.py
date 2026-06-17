"""Envio de inscricao em curso via multipart form-data ou JSON."""


class EnviadorInscricaoCurso:
    def enviar_multipart(self, curso_id, dados_aluno: dict, certificado_pdf=None):
        boundary = "----CursoBoundary7d41b"
        linhas = [
            f"--{boundary}",
            'Content-Disposition: form-data; name="curso_id"',
            "",
            str(curso_id),
            f"--{boundary}",
            'Content-Disposition: form-data; name="nome_aluno"',
            "",
            dados_aluno["nome_aluno"],
            f"--{boundary}",
            'Content-Disposition: form-data; name="email"',
            "",
            dados_aluno["email"],
        ]
        if certificado_pdf:
            linhas += [
                f"--{boundary}",
                'Content-Disposition: form-data; name="certificado"; filename="certificado.pdf"',
                "Content-Type: application/pdf",
                "",
                certificado_pdf,
            ]
        linhas.append(f"--{boundary}--")
        corpo = "\r\n".join(linhas)
        return self._enviar(corpo, f"multipart/form-data; boundary={boundary}")

    def enviar_json(self, curso_id, dados_aluno: dict, certificado_pdf=None):
        import json
        payload = {"curso_id": curso_id, **dados_aluno}
        if certificado_pdf:
            payload["certificado_base64"] = certificado_pdf
        return self._enviar(json.dumps(payload), "application/json")

    def _enviar(self, corpo, content_type) -> dict: ...
