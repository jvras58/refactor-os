"""Geracao de relatorios de vendas e de estoque."""


class RelatorioVendas:
    def gerar(self, dados):
        conexao = abrir_conexao()
        dados_brutos = conexao.query("SELECT * FROM vendas")
        linhas = [self._formatar_venda(d) for d in dados_brutos]
        cabecalho = "Relatorio de Vendas\n" + "-" * 20
        conexao.fechar()
        return cabecalho + "\n".join(linhas)

    def _formatar_venda(self, d): ...


class RelatorioEstoque:
    def gerar(self, dados):
        conexao = abrir_conexao()
        dados_brutos = conexao.query("SELECT * FROM estoque")
        linhas = [self._formatar_item(d) for d in dados_brutos]
        cabecalho = "Relatorio de Estoque\n" + "-" * 20
        conexao.fechar()
        return cabecalho + "\n".join(linhas)

    def _formatar_item(self, d): ...


def abrir_conexao(): ...
