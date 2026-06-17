"""Calculo de nota a partir das tentativas de resposta de um exercicio."""


class CalculadoraNotaTentativas:
    def calcular(self, criterio: str, tentativas: list[float]) -> float:
        if criterio == "ultima_tentativa":
            return tentativas[-1]
        elif criterio == "media":
            return sum(tentativas) / len(tentativas)
        elif criterio == "maior_nota":
            return max(tentativas)
        elif criterio == "primeira_tentativa":
            return tentativas[0]
        elif criterio == "media_ponderada_recente":
            pesos = list(range(1, len(tentativas) + 1))
            return sum(t * p for t, p in zip(tentativas, pesos)) / sum(pesos)
        else:
            raise ValueError(f"criterio de calculo de nota desconhecido: {criterio}")


class BoletimAluno:
    def __init__(self):
        self._calculadora = CalculadoraNotaTentativas()

    def registrar_nota_exercicio(self, identificacao: dict, tentativas, criterio_exercicio):
        nota = self._calculadora.calcular(criterio_exercicio, tentativas)
        return {**identificacao, "nota": nota}
