"""Importacao de registros a partir de arquivos em diferentes formatos."""


class ImportadorCSV:
    def importar(self, caminho):
        arquivo = abrir_arquivo(caminho)
        registros = self._parsear_csv(arquivo)
        registros_validos = [r for r in registros if self._validar(r)]
        salvar_no_banco(registros_validos)
        arquivo.close()
        return len(registros_validos)

    def _parsear_csv(self, arquivo): ...
    def _validar(self, registro): ...


class ImportadorJSON:
    def importar(self, caminho):
        arquivo = abrir_arquivo(caminho)
        registros = self._parsear_json(arquivo)
        registros_validos = [r for r in registros if self._validar(r)]
        salvar_no_banco(registros_validos)
        arquivo.close()
        return len(registros_validos)

    def _parsear_json(self, arquivo): ...
    def _validar(self, registro): ...


def abrir_arquivo(caminho): ...
def salvar_no_banco(registros): ...
