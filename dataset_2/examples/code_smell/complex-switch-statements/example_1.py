"""Cálculo de frete por tipo de transportadora."""


def calcular_frete(tipo: str, peso: float, distancia: float) -> float:
    if tipo == "sedex":
        return peso * 2.5 + distancia * 0.1
    elif tipo == "pac":
        return peso * 1.2 + distancia * 0.05
    elif tipo == "transportadora":
        return peso * 0.8 + distancia * 0.15 + 10
    elif tipo == "retirada":
        return 0
    elif tipo == "internacional":
        return peso * 5.0 + distancia * 0.3 + 50
    else:
        raise ValueError(f"tipo de frete desconhecido: {tipo}")
