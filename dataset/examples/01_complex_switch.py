"""Bad smell: Complex/Long Switch Statements — esperado: Strategy Pattern."""


def calculate_shipping(country: str, weight_kg: float) -> float:
    if country == "BR":
        if weight_kg < 1:
            return 15.0
        elif weight_kg < 5:
            return 35.0
        else:
            return 80.0
    elif country == "US":
        if weight_kg < 1:
            return 10.0
        elif weight_kg < 5:
            return 25.0
        else:
            return 60.0
    elif country == "DE":
        if weight_kg < 1:
            return 12.0
        elif weight_kg < 5:
            return 28.0
        else:
            return 70.0
    elif country == "JP":
        return 18.0 + weight_kg * 4.5
    else:
        raise ValueError(f"unsupported country: {country}")
