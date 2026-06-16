"""Montagem de pizza com varias opcoes de customizacao."""


class Pizza:
    def __init__(self, tamanho, borda=None, queijo_extra=False,
                 cobertura_1=None, cobertura_2=None, cobertura_3=None,
                 molho="tomate", ponto_forno="normal"):
        self.tamanho = tamanho
        self.borda = borda
        self.queijo_extra = queijo_extra
        self.coberturas = [c for c in (cobertura_1, cobertura_2, cobertura_3) if c]
        self.molho = molho
        self.ponto_forno = ponto_forno


# chamada — precisa passar None nas posicoes que nao quer usar
pizza = Pizza("grande", None, True, "calabresa", None, None, "tomate", "bem-passada")
