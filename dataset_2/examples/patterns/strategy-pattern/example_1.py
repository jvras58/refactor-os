"""Calculo de desconto com base no perfil e no contexto da compra."""


def calcular_desconto(valor: float, is_vip: bool, is_primeira_compra: bool,
                       is_black_friday: bool) -> float:
    desconto = 0.0
    if is_black_friday:
        desconto = 0.30
    elif is_vip and is_primeira_compra:
        desconto = 0.25
    elif is_vip:
        desconto = 0.15
    elif is_primeira_compra:
        desconto = 0.10
    else:
        desconto = 0.0
    return valor * (1 - desconto)
