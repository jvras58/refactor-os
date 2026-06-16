"""Importacao de registros em lote a partir de arquivos."""


class ImportadorLoteCSV:
    def importar(self, caminho):
        arquivo = self._abrir(caminho)
        cabecalho = self._ler_cabecalho_csv(arquivo)
        total, erros = 0, 0
        for linha in arquivo:
            if self._processar_linha_csv(linha, cabecalho):
                total += 1
            else:
                erros += 1
        arquivo.close()
        return {"total": total, "erros": erros}

    def _abrir(self, caminho): ...
    def _ler_cabecalho_csv(self, arquivo): ...
    def _processar_linha_csv(self, linha, cabecalho): ...


class ImportadorLoteXML:
    def importar(self, caminho):
        arquivo = self._abrir(caminho)
        cabecalho = self._ler_cabecalho_xml(arquivo)
        total, erros = 0, 0
        for linha in arquivo:
            if self._processar_linha_xml(linha, cabecalho):
                total += 1
            else:
                erros += 1
        arquivo.close()
        return {"total": total, "erros": erros}

    def _abrir(self, caminho): ...
    def _ler_cabecalho_xml(self, arquivo): ...
    def _processar_linha_xml(self, linha, cabecalho): ...
