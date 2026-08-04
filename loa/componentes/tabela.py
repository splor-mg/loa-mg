"""Tabela — o coração do site.

É aqui que 600 páginas de PDF viram uma tela. A tabela sai completa
(nenhum dado é omitido), mas:

  * níveis hierárquicos começam recolhidos e abrem ao clique;
  * há filtro por texto, ordenação por coluna e exportação;
  * termos técnicos ganham tooltip do glossário.

A hierarquia sai da própria coluna de nível dos dados — sem tabela
auxiliar, conforme a regra do projeto.
"""

import html

from ..dados import ordenar
from ..formato import formatar, para_decimal

LARGURA_MINIMA_NUMERO = 12.0
LARGURA_MINIMA_TEXTO = 14.0
LARGURA_UTIL_TIPICA = 62.0


def _grupo_colunas(colunas):
    """Decide a largura das colunas; devolve (colgroup, estilo da tabela).

    Duas situacoes, tratadas de forma diferente:

    1. A tabela CABE na largura disponivel. Distribuimos o espaco em
       porcentagens: as numericas recebem uma fatia fixa e o texto fica
       com o resto. Sem isto o navegador da a coluna de texto a largura
       do seu conteudo mais longo e empurra as demais para fora, gerando
       barra de rolagem numa tabela que caberia.

    2. A tabela NAO cabe - muitas colunas de valores altos, como no
       Investimento das estatais. Ai espremer nao ajuda: 80 px por coluna
       quebra cada valor em tres linhas. Melhor dar a cada coluna a
       largura minima legivel e deixar rolar na horizontal, que e o caso
       em que a barra de rolagem se justifica.

    Um valor como "R$ 117.014.652.734,00" ocupa cerca de 11,5rem na fonte
    da tabela, contando o padding da celula. Abaixo disso ele quebra em
    duas ou tres linhas e a coluna vira uma torre de digitos.
    """
    numericas = sum(1 for c in colunas if c.get("tipo") != "texto")
    textuais = len(colunas) - numericas
    if not textuais:
        return "", ""

    minimo = numericas * LARGURA_MINIMA_NUMERO + textuais * LARGURA_MINIMA_TEXTO

    if minimo > LARGURA_UTIL_TIPICA:
        tags = []
        for coluna in colunas:
            largura = (
                LARGURA_MINIMA_NUMERO
                if coluna.get("tipo") != "texto"
                else LARGURA_MINIMA_TEXTO
            )
            tags.append('<col style="width:%.4grem">' % largura)
        estilo = ' style="min-width:%.4grem"' % minimo
        return "<colgroup>" + "".join(tags) + "</colgroup>", estilo

    fatia_numero = (LARGURA_MINIMA_NUMERO / LARGURA_UTIL_TIPICA) * 100
    # 97,5% e nao 100%: o arredondamento das larguras de coluna pelo
    # navegador sobrava alguns pixels e reacendia a barra de rolagem
    largura_texto = (97.5 - fatia_numero * numericas) / textuais

    tags = []
    for coluna in colunas:
        largura = fatia_numero if coluna.get("tipo") != "texto" else largura_texto
        tags.append('<col style="width:%.4g%%">' % largura)
    return "<colgroup>" + "".join(tags) + "</colgroup>", ""


def _profundidades(linhas: list[dict], campo_nivel: str) -> list[int]:
    """Profundidade de cada linha na ÁRVORE, contando degraus reais.

    Não é o mesmo que o número do nível. A classificação orçamentária pula
    níveis: "DESPESAS CORRENTES" é nível 1 e seu filho direto é nível 3 —
    não existe nível 2 nesse ramo. Recolher tudo com "nível maior que 2"
    esconderia o primeiro degrau da árvore e a linha ficaria sem nada para
    abrir.

    Aqui a profundidade é contada empilhando ancestrais: o primeiro degrau
    é sempre 1, o seguinte 2, independentemente dos números de nível.
    """
    profundidades = []
    pilha: list[int] = []
    for linha in linhas:
        nivel = int(linha.get(campo_nivel) or 1)
        while pilha and pilha[-1] >= nivel:
            pilha.pop()
        pilha.append(nivel)
        profundidades.append(len(pilha))
    return profundidades


def _cabecalho(colunas: list[dict]) -> str:
    celulas = []
    for i, coluna in enumerate(colunas):
        classe = (
            "loa-col--numero" if coluna.get("tipo") != "texto" else "loa-col--texto"
        )
        titulo = html.escape(coluna["titulo"])
        celulas.append(
            f'<th class="{classe}" data-coluna="{i}" '
            f'data-tipo="{coluna.get("tipo", "texto")}" tabindex="0" '
            f'role="columnheader" aria-sort="none">{titulo}</th>'
        )
    return "<tr>" + "".join(celulas) + "</tr>"


def _linha_totais(linhas, colunas, campo_nivel):
    """Linha de total: soma apenas o nível mais alto, para não contar duas vezes."""
    if campo_nivel:
        niveis = [int(l.get(campo_nivel) or 0) for l in linhas]
        if not niveis:
            return ""
        topo = min(niveis)
        base = [l for l in linhas if int(l.get(campo_nivel) or 0) == topo]
    else:
        base = linhas

    celulas = []
    for i, coluna in enumerate(colunas):
        if coluna.get("tipo") in ("dinheiro", "quantidade"):
            total = sum(
                (para_decimal(l.get(coluna["campo"])) for l in base),
                start=para_decimal(0),
            )
            celulas.append(
                f'<td class="loa-col--numero">{formatar(total, coluna["tipo"])}</td>'
            )
        elif i == 0:
            celulas.append('<td class="loa-col--texto">TOTAL</td>')
        else:
            celulas.append("<td></td>")
    return '<tr class="loa-total">' + "".join(celulas) + "</tr>"


def montar(
    linhas: list[dict],
    colunas: list[dict],
    glossario,
    identificador: str,
    hierarquia: dict | None = None,
    ordenar_por: str | None = None,
    mostrar_total: bool = True,
    nivel_aberto: int = 2,
) -> str:
    """Devolve o HTML completo do bloco de tabela."""
    campo_nivel = (hierarquia or {}).get("campo_nivel")

    if ordenar_por and not campo_nivel:
        linhas = ordenar(linhas, ordenar_por, desc=True)

    profundidades = _profundidades(linhas, campo_nivel) if campo_nivel else []

    corpo = []
    for numero, linha in enumerate(linhas):
        nivel = int(linha.get(campo_nivel) or 1) if campo_nivel else 1
        recolhida = campo_nivel and profundidades[numero] > nivel_aberto

        celulas = []
        for i, coluna in enumerate(colunas):
            bruto = linha.get(coluna["campo"], "")
            tipo = coluna.get("tipo", "texto")

            if tipo == "texto":
                conteudo = glossario.marcar(bruto)
                if i == 0 and campo_nivel:
                    # recuo pela profundidade: com níveis que pulam, usar o
                    # número do nível abriria buracos visuais enormes
                    recuo = profundidades[numero] - 1
                    conteudo = (
                        f'<span class="loa-recuo" style="--nivel:{recuo}"></span>'
                        f'<span class="loa-rotulo">{conteudo}</span>'
                    )
                celulas.append(f'<td class="loa-col--texto">{conteudo}</td>')
            else:
                texto = formatar(bruto, tipo)
                celulas.append(
                    f'<td class="loa-col--numero" data-valor="{para_decimal(bruto)}">{texto}</td>'
                )

        atributos = [
            f'data-nivel="{nivel}"',
            f'data-num="{numero}"',
        ]
        if campo_nivel:
            atributos.append(f'data-profundidade="{profundidades[numero]}"')
        if recolhida:
            # `data-recolhida` = escondida pela hierarquia.
            # `data-oculta-filtro` (posto pelo JS) = escondida pelo filtro.
            # São estados independentes; o `hidden` é o resultado dos dois.
            # Antes os dois escreviam direto em `hidden` e se apagavam
            # mutuamente: filtrar destruía a árvore, e limpar o filtro
            # deixava a tabela num estado que não era nem um nem outro.
            atributos.append("data-recolhida hidden")
        corpo.append(f"<tr {' '.join(atributos)}>" + "".join(celulas) + "</tr>")

    if mostrar_total:
        corpo.append(_linha_totais(linhas, colunas, campo_nivel))

    botao_expandir = ""
    if campo_nivel:
        botao_expandir = (
            '<button type="button" class="loa-botao" data-acao="expandir">'
            "Expandir tudo</button>"
        )

    grupo, estilo_tabela = _grupo_colunas(colunas)

    return f"""
<div class="loa-tabela" id="tabela-{identificador}" data-id="{identificador}">
  <div class="loa-ferramentas">
    <input type="search" class="loa-filtro" aria-label="Filtrar linhas da tabela"
           placeholder="Filtrar nesta tabela...">
    {botao_expandir}
    <button type="button" class="loa-botao" data-acao="csv">Baixar CSV</button>
    <button type="button" class="loa-botao" data-acao="imprimir">Imprimir</button>
    <span class="loa-contador" aria-live="polite"></span>
  </div>
  <div class="loa-rolagem">
    <table{estilo_tabela}>
      {grupo}
      <thead>{_cabecalho(colunas)}</thead>
      <tbody>
        {"".join(corpo)}
      </tbody>
    </table>
  </div>
</div>
""".strip()
