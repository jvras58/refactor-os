"""Envio de notificacao para diferentes canais de comunicacao."""


def enviar_notificacao(canal: str, destinatario: str, mensagem: str) -> bool:
    if canal == "email":
        assunto = "Nova notificacao"
        corpo = f"<html><body>{mensagem}</body></html>"
        return _enviar_smtp(destinatario, assunto, corpo)
    elif canal == "sms":
        texto = mensagem[:160]
        return _enviar_sms(destinatario, texto)
    elif canal == "push":
        payload = {"to": destinatario, "body": mensagem[:200]}
        return _enviar_push(payload)
    elif canal == "whatsapp":
        texto = f"*Notificacao*\n{mensagem}"
        return _enviar_whatsapp(destinatario, texto)
    elif canal == "webhook":
        payload = {"destinatario": destinatario, "mensagem": mensagem}
        return _enviar_webhook(payload)
    else:
        raise ValueError(f"canal de notificacao desconhecido: {canal}")


def _enviar_smtp(destinatario, assunto, corpo) -> bool: ...
def _enviar_sms(destinatario, texto) -> bool: ...
def _enviar_push(payload) -> bool: ...
def _enviar_whatsapp(destinatario, texto) -> bool: ...
def _enviar_webhook(payload) -> bool: ...
