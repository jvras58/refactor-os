"""Código limpo: classe coesa e pequena (SRP respeitado). Nenhum smell esperado."""


class TemperatureConverter:
    def to_fahrenheit(self, celsius: float) -> float:
        return celsius * 9 / 5 + 32

    def to_celsius(self, fahrenheit: float) -> float:
        return (fahrenheit - 32) * 5 / 9

    def to_kelvin(self, celsius: float) -> float:
        return celsius + 273.15
