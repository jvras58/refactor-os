"""Montagem de notificacao push para enviar via APNs (iOS) ou FCM (Android)."""


class NotificacaoPush:
    def montar_apns(self, titulo, corpo, opcoes: dict | None = None):
        opcoes = opcoes or {}
        payload = {"aps": {"alert": {"title": titulo, "body": corpo}}}
        if "badge" in opcoes:
            payload["aps"]["badge"] = opcoes["badge"]
        if "som" in opcoes:
            payload["aps"]["sound"] = opcoes["som"]
        if "dados_customizados" in opcoes:
            payload.update(opcoes["dados_customizados"])
        return payload

    def montar_fcm(self, titulo, corpo, opcoes: dict | None = None):
        opcoes = opcoes or {}
        payload = {"notification": {"title": titulo, "body": corpo}}
        if "som" in opcoes:
            payload["android"] = {"notification": {"sound": opcoes["som"]}}
        if "badge" in opcoes:
            payload.setdefault("data", {})["badge"] = str(opcoes["badge"])
        if "dados_customizados" in opcoes:
            payload.setdefault("data", {}).update(opcoes["dados_customizados"])
        return payload
