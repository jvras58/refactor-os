"""Processamento de atividades avaliativas em uma plataforma educacional."""


class ProcessadorQuestionarioObjetivo:
    def processar(self, atividade, entrega_aluno):
        if not atividade.disponivel:
            raise ValueError("atividade indisponivel")
        if entrega_aluno.data_envio > atividade.prazo_final:
            raise ValueError("entrega fora do prazo")

        respostas = entrega_aluno.respostas
        acertos = sum(1 for r, gabarito in zip(respostas, atividade.gabarito) if r == gabarito)
        nota = (acertos / len(atividade.gabarito)) * 10

        resultado = {"aluno_id": entrega_aluno.aluno_id, "atividade_id": atividade.id, "nota": nota}
        salvar_resultado(resultado)

        feedback = f"Voce acertou {acertos} de {len(atividade.gabarito)} questoes."
        notificar_aluno(entrega_aluno.aluno_id, feedback)
        return resultado


class ProcessadorRedacao:
    def processar(self, atividade, entrega_aluno):
        if not atividade.disponivel:
            raise ValueError("atividade indisponivel")
        if entrega_aluno.data_envio > atividade.prazo_final:
            raise ValueError("entrega fora do prazo")

        avaliacao_professor = buscar_avaliacao_manual(entrega_aluno.id)
        nota = avaliacao_professor.nota_final

        resultado = {"aluno_id": entrega_aluno.aluno_id, "atividade_id": atividade.id, "nota": nota}
        salvar_resultado(resultado)

        feedback = avaliacao_professor.comentarios
        notificar_aluno(entrega_aluno.aluno_id, feedback)
        return resultado


class ProcessadorExercicioProgramacao:
    def processar(self, atividade, entrega_aluno):
        if not atividade.disponivel:
            raise ValueError("atividade indisponivel")
        if entrega_aluno.data_envio > atividade.prazo_final:
            raise ValueError("entrega fora do prazo")

        resultados_testes = executar_testes_automatizados(entrega_aluno.codigo, atividade.casos_teste)
        nota = (sum(1 for r in resultados_testes if r.passou) / len(resultados_testes)) * 10

        resultado = {"aluno_id": entrega_aluno.aluno_id, "atividade_id": atividade.id, "nota": nota}
        salvar_resultado(resultado)

        feedback = "\n".join(f"Teste {r.nome}: {'OK' if r.passou else 'FALHOU'}" for r in resultados_testes)
        notificar_aluno(entrega_aluno.aluno_id, feedback)
        return resultado


def salvar_resultado(resultado): ...
def notificar_aluno(aluno_id, feedback): ...
def buscar_avaliacao_manual(entrega_id): ...
def executar_testes_automatizados(codigo, casos_teste): ...
