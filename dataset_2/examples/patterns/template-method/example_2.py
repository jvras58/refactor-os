"""Execucao de testes de integracao contra diferentes recursos."""


class TesteIntegracaoApi:
    def executar(self):
        self._log("iniciando teste")
        contexto = self._preparar_ambiente()
        try:
            resultado = self._chamar_api(contexto)
            self._verificar_resultado(resultado)
        finally:
            self._limpar_ambiente(contexto)
        self._log("teste finalizado")

    def _preparar_ambiente(self): ...
    def _chamar_api(self, contexto): ...
    def _verificar_resultado(self, resultado): ...
    def _limpar_ambiente(self, contexto): ...
    def _log(self, mensagem): ...


class TesteIntegracaoBanco:
    def executar(self):
        self._log("iniciando teste")
        contexto = self._preparar_conexao()
        try:
            resultado = self._executar_query(contexto)
            self._verificar_linhas(resultado)
        finally:
            self._fechar_conexao(contexto)
        self._log("teste finalizado")

    def _preparar_conexao(self): ...
    def _executar_query(self, contexto): ...
    def _verificar_linhas(self, resultado): ...
    def _fechar_conexao(self, contexto): ...
    def _log(self, mensagem): ...
