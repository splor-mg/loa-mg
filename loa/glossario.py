"""Glossário embutido.

Em vez de uma página separada que ninguém visita, cada termo técnico
vira um tooltip no lugar onde ele aparece. Basta cadastrar o termo em
config/glossario.yml.
"""

import html
import re


class Glossario:
    def __init__(self, termos: dict[str, str]):
        # Do mais longo para o mais curto: assim "RECEITA CORRENTE LÍQUIDA"
        # é reconhecido antes de "RECEITA CORRENTE", e a alternância do
        # regex abaixo escolhe sempre o termo mais específico.
        self.termos = dict(
            sorted(termos.items(), key=lambda item: len(item[0]), reverse=True)
        )
        if self.termos:
            alternativas = "|".join(re.escape(t) for t in self.termos)
            self._padrao = re.compile(rf"\b(?:{alternativas})\b", re.IGNORECASE)
        else:
            self._padrao = None

        # busca sem depender de maiúsculas/minúsculas
        self._definicoes = {t.casefold(): d for t, d in self.termos.items()}

    def marcar(self, texto: str) -> str:
        """Devolve HTML com os termos conhecidos envolvidos em <abbr>.

        A substituição acontece em UMA ÚNICA passada, com um regex que
        alterna entre todos os termos. Isso é essencial: numa implementação
        com uma passada por termo, a segunda passada encontraria os termos
        citados dentro do atributo `title` que a primeira acabou de inserir,
        aninharia tags ali dentro e quebraria as aspas do atributo — o HTML
        resultante vaza como texto na tela.
        """
        if not texto or self._padrao is None:
            return ""

        seguro = html.escape(str(texto))
        usados: set[str] = set()

        def troca(achado: re.Match) -> str:
            palavra = achado.group(0)
            chave = palavra.casefold()
            # um tooltip por termo em cada célula: repetir polui a leitura
            if chave in usados:
                return palavra
            usados.add(chave)
            definicao = html.escape(self._definicoes[chave], quote=True)
            return f'<abbr title="{definicao}">{palavra}</abbr>'

        return self._padrao.sub(troca, seguro)

    def como_markdown(self) -> str:
        """Página de glossário completa, em ordem alfabética."""
        linhas = ["| Termo | O que significa |", "| --- | --- |"]
        for termo in sorted(self.termos, key=str.casefold):
            definicao = self.termos[termo].replace("|", "\\|")
            linhas.append(f"| **{termo}** | {definicao} |")
        return "\n".join(linhas)
