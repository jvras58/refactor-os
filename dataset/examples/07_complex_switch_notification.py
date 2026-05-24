"""Bad smell: Complex/Long Switch Statements - esperado: Strategy Pattern."""


def prepare_notification(channel: str, recipient: str, subject: str, message: str, priority: str) -> dict:
    if channel == "email":
        payload = {
            "to": recipient,
            "subject": subject,
            "body": message,
            "headers": {"X-Priority": priority.upper()},
        }
        retry_limit = 3
        delivery_window = "business_hours"
    elif channel == "sms":
        payload = {
            "phone": recipient,
            "text": f"{subject}: {message}"[:160],
        }
        retry_limit = 2
        delivery_window = "anytime"
    elif channel == "push":
        payload = {
            "device_token": recipient,
            "title": subject[:40],
            "body": message[:120],
            "silent": priority == "low",
        }
        retry_limit = 1
        delivery_window = "anytime"
    elif channel == "slack":
        payload = {
            "user": recipient,
            "blocks": [{"type": "section", "text": f"*{subject}*\n{message}"}],
        }
        retry_limit = 2
        delivery_window = "workday"
    elif channel == "letter":
        payload = {
            "address": recipient,
            "print_template": "formal_notice",
            "content": f"{subject}\n\n{message}",
        }
        retry_limit = 0
        delivery_window = "postal_service"
    else:
        raise ValueError(f"unsupported notification channel: {channel}")

    return {"channel": channel, "payload": payload, "retry_limit": retry_limit, "delivery_window": delivery_window}
