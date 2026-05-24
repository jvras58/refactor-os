"""Bad smell: Long Parameter List - esperado: Builder/Parameter Object."""


def create_user_profile(
    user_id: int,
    first_name: str,
    last_name: str,
    email: str,
    phone: str,
    street: str,
    city: str,
    state: str,
    country: str,
    postal_code: str,
    newsletter_enabled: bool,
    two_factor_enabled: bool,
    preferred_language: str,
    timezone: str,
) -> dict:
    display_name = f"{first_name} {last_name}".strip()
    address = {
        "street": street,
        "city": city,
        "state": state,
        "country": country,
        "postal_code": postal_code,
    }
    preferences = {
        "newsletter_enabled": newsletter_enabled,
        "two_factor_enabled": two_factor_enabled,
        "preferred_language": preferred_language,
        "timezone": timezone,
    }
    return {
        "id": user_id,
        "name": display_name,
        "email": email,
        "phone": phone,
        "address": address,
        "preferences": preferences,
    }
