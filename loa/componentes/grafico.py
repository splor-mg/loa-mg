"""Gráficos.

Desenhados como SVG direto em Python — sem biblioteca de gráficos em
JavaScript. Assim o site continua 100% Python, carrega instantâneo,
funciona sem internet e imprime bem.

No YAML:

    graficos:
      - tipo: barras          # barras | rosca | barras_empilhadas
        titulo: 10 maiores orçamentos
        rotulo: uo_nome
        valor: total
        limite: 10
"""

import html
from decimal import Decimal

from ..dados import filtrar, ordenar
from ..formato import para_decimal, percentual, resumido, resumido_quantidade

# Escala da bandeira de Minas: do vermelho profundo ao quase-branco.
# A ordem importa — as barras saem ordenadas do maior para o menor, então
# a intensidade da cor acompanha a posição no ranking.
PALETA = [
    "#501313", "#791f1f", "#a32d2d", "#c23c3a", "#e24b4a",
    "#ea6f6d", "#f09595", "#f4abab", "#f7c1c1", "#fbdada",
]


def _curto(valor, config) -> str:
    """Formata o valor conforme o tipo declarado no gráfico."""
    if config.get("tipo_valor") == "quantidade":
        return resumido_quantidade(valor)
    return resumido(valor)


def _preparar(linhas, config):
    campo_rotulo, campo_valor = config["rotulo"], config["valor"]
    linhas = filtrar(linhas, config.get("filtro", {}))
    dados = [
        (str(l.get(campo_rotulo, "")), para_decimal(l.get(campo_valor)))
        for l in ordenar(linhas, campo_valor, desc=True)
        if para_decimal(l.get(campo_valor)) > 0
    ]
    limite = config.get("limite")
    if limite and len(dados) > limite:
        resto = sum((v for _, v in dados[limite:]), start=Decimal(0))
        dados = dados[:limite] + [("Demais", resto)]
    return dados


def barras(linhas, config) -> str:
    dados = _preparar(linhas, config)
    if not dados:
        return ""

    maior = max(v for _, v in dados)
    total = sum((v for _, v in dados), start=Decimal(0))

    # Medidas em unidades do viewBox — o SVG é escalado para a largura
    # disponível, então elas se comportam como proporções.
    altura_barra, espaco = 30, 12
    largura = 1000
    margem_esq = 400            # faixa reservada aos nomes
    faixa_valor = 230           # faixa reservada ao valor + percentual

    # Estimar a largura de um texto em SVG é impreciso — nomes de órgãos vêm
    # em CAIXA ALTA, cujas letras são bem mais largas que a média. Por isso
    # há duas defesas: cortar nomes muito longos por estimativa generosa, e
    # usar `textLength` para garantir que o que sobrou caiba na faixa.
    # `textLength` faz o navegador ajustar o texto à largura exata, então
    # nada vaza, mesmo que a estimativa erre.
    faixa_nome = margem_esq - 16
    LARGURA_CARACTERE = 17 * 0.62      # caixa alta é larga
    max_letras = int(faixa_nome / LARGURA_CARACTERE)

    altura = len(dados) * (altura_barra + espaco) + 20

    partes = [
        f'<svg class="loa-grafico" viewBox="0 0 {largura} {altura}" '
        f'role="img" aria-label="{html.escape(config["titulo"])}">'
    ]
    for i, (rotulo, valor) in enumerate(dados):
        y = i * (altura_barra + espaco) + 8
        disponivel = largura - margem_esq - faixa_valor
        comprimento = int((valor / maior) * disponivel) if maior else 0
        curto = (rotulo if len(rotulo) <= max_letras
                 else rotulo[:max_letras - 1].rstrip() + "…")

        # Comprime só quando a estimativa indica que não cabe; textos
        # curtos ficam com o espaçamento natural.
        # Margem de 10%: a estimativa erra para mais e para menos conforme
        # as letras do nome, então o textLength entra um pouco antes do
        # limite teórico em vez de só quando a conta estoura.
        estimado = len(curto) * LARGURA_CARACTERE
        ajuste = (f' textLength="{faixa_nome}" lengthAdjust="spacingAndGlyphs"'
                  if estimado > faixa_nome * 0.9 else "")
        cor = PALETA[i % len(PALETA)]
        partes.append(
            f'<text x="{margem_esq - 12}" y="{y + 20}" text-anchor="end"{ajuste} '
            f'class="loa-grafico__rotulo">{html.escape(curto)}'
            f'<title>{html.escape(rotulo)}</title></text>'
            f'<rect x="{margem_esq}" y="{y}" width="{max(comprimento, 2)}" height="{altura_barra}" '
            f'rx="3" fill="{cor}"><title>{html.escape(rotulo)}: {_curto(valor, config)}</title></rect>'
            f'<text x="{margem_esq + max(comprimento, 2) + 10}" y="{y + 20}" '
            f'class="loa-grafico__valor">{_curto(valor, config)} '
            f'({percentual(valor, total)})</text>'
        )
    partes.append("</svg>")
    return "".join(partes)


def rosca(linhas, config) -> str:
    import math

    dados = _preparar(linhas, config)
    if not dados:
        return ""

    total = sum((v for _, v in dados), start=Decimal(0))
    if total == 0:
        return ""

    # A altura acompanha o número de itens da legenda, senão as últimas
    # linhas ficam de fora do viewBox quando há muitas fatias.
    cx, cy, raio, grossura = 170, 180, 130, 52
    largura, legenda_x = 1000, 370
    faixa_legenda = largura - legenda_x - 10
    altura = max(360, 44 + len(dados) * 30)

    # Mesma proteção das barras: corta por estimativa e usa textLength
    # como garantia de que nada escapa da caixa.
    LARGURA_CARACTERE = 17 * 0.58

    partes = [
        f'<svg class="loa-grafico loa-grafico--rosca" viewBox="0 0 {largura} {altura}" '
        f'role="img" aria-label="{html.escape(config["titulo"])}">'
    ]
    angulo = -math.pi / 2
    for i, (rotulo, valor) in enumerate(dados):
        fatia = float(valor / total) * 2 * math.pi
        fim = angulo + fatia
        grande = 1 if fatia > math.pi else 0
        x1, y1 = cx + raio * math.cos(angulo), cy + raio * math.sin(angulo)
        x2, y2 = cx + raio * math.cos(fim), cy + raio * math.sin(fim)
        cor = PALETA[i % len(PALETA)]
        partes.append(
            f'<path d="M {x1:.2f} {y1:.2f} A {raio} {raio} 0 {grande} 1 {x2:.2f} {y2:.2f}" '
            f'fill="none" stroke="{cor}" stroke-width="{grossura}" '
            f'stroke-linecap="butt" class="loa-fatia">'
            f"<title>{html.escape(rotulo)}: {_curto(valor, config)} ({percentual(valor, total)})</title></path>"
        )
        y = 34 + i * 30
        texto = f"{rotulo} — {_curto(valor, config)} ({percentual(valor, total)})"
        max_letras = int(faixa_legenda / LARGURA_CARACTERE)
        if len(texto) > max_letras:
            # encurta o NOME, nunca o valor: o número é o que interessa
            sobra = max_letras - len(texto) + len(rotulo) - 1
            curto = rotulo[:max(sobra, 8)].rstrip() + "…"
            texto = f"{curto} — {_curto(valor, config)} ({percentual(valor, total)})"
        ajuste = (f' textLength="{faixa_legenda}" lengthAdjust="spacingAndGlyphs"'
                  if len(texto) * LARGURA_CARACTERE > faixa_legenda * 0.95 else "")
        partes.append(
            f'<rect x="{legenda_x - 24}" y="{y - 13}" width="15" height="15" rx="3" fill="{cor}"/>'
            f'<text x="{legenda_x}" y="{y}"{ajuste} class="loa-grafico__rotulo">'
            f"{html.escape(texto)}<title>{html.escape(rotulo)}</title></text>"
        )
    partes.append(
        f'<text x="{cx}" y="{cy - 2}" text-anchor="middle" class="loa-grafico__centro">'
        f"{_curto(total, config)}</text>"
        f'<text x="{cx}" y="{cy + 24}" text-anchor="middle" class="loa-grafico__rotulo">total</text>'
    )
    partes.append("</svg>")
    return "".join(partes)


TIPOS = {"barras": barras, "rosca": rosca}


def montar(linhas, config) -> str:
    desenhar = TIPOS.get(config.get("tipo", "barras"))
    if not desenhar:
        raise ValueError(f"Tipo de gráfico desconhecido: {config.get('tipo')}")

    svg = desenhar(linhas, config)
    if not svg:
        return ""

    nota = f'<p class="loa-figura__nota">{config["nota"]}</p>' if config.get("nota") else ""
    return (
        f'<figure class="loa-figura">'
        f'<figcaption>{html.escape(config["titulo"])}</figcaption>{svg}{nota}</figure>'
    )
