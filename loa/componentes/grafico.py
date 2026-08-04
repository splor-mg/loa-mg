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
from ..formato import para_decimal, percentual, resumido

# Escala da bandeira de Minas: do vermelho profundo ao quase-branco.
# A ordem importa — as barras saem ordenadas do maior para o menor, então
# a intensidade da cor acompanha a posição no ranking.
PALETA = [
    "#501313", "#791f1f", "#a32d2d", "#c23c3a", "#e24b4a",
    "#ea6f6d", "#f09595", "#f4abab", "#f7c1c1", "#fbdada",
]


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
    altura_barra, espaco = 26, 10
    largura, margem_esq = 900, 330
    altura = len(dados) * (altura_barra + espaco) + 20

    partes = [
        f'<svg class="loa-grafico" viewBox="0 0 {largura} {altura}" '
        f'role="img" aria-label="{html.escape(config["titulo"])}">'
    ]
    for i, (rotulo, valor) in enumerate(dados):
        y = i * (altura_barra + espaco) + 8
        comprimento = int((valor / maior) * (largura - margem_esq - 190)) if maior else 0
        curto = rotulo if len(rotulo) <= 46 else rotulo[:44] + "…"
        cor = PALETA[i % len(PALETA)]
        partes.append(
            f'<text x="{margem_esq - 10}" y="{y + 18}" text-anchor="end" '
            f'class="loa-grafico__rotulo">{html.escape(curto)}<title>{html.escape(rotulo)}</title></text>'
            f'<rect x="{margem_esq}" y="{y}" width="{max(comprimento, 2)}" height="{altura_barra}" '
            f'rx="3" fill="{cor}"><title>{html.escape(rotulo)}: {resumido(valor)}</title></rect>'
            f'<text x="{margem_esq + max(comprimento, 2) + 8}" y="{y + 18}" '
            f'class="loa-grafico__valor">{resumido(valor)} '
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

    cx, cy, raio, grossura = 150, 150, 120, 46
    partes = [
        f'<svg class="loa-grafico loa-grafico--rosca" viewBox="0 0 640 300" '
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
            f"<title>{html.escape(rotulo)}: {resumido(valor)} ({percentual(valor, total)})</title></path>"
        )
        y = 30 + i * 26
        partes.append(
            f'<rect x="320" y="{y - 11}" width="13" height="13" rx="2" fill="{cor}"/>'
            f'<text x="342" y="{y}" class="loa-grafico__rotulo">'
            f"{html.escape(rotulo[:38])} — {resumido(valor)} ({percentual(valor, total)})</text>"
        )
    partes.append(
        f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" class="loa-grafico__centro">'
        f"{resumido(total)}</text>"
        f'<text x="{cx}" y="{cy + 18}" text-anchor="middle" class="loa-grafico__rotulo">total</text>'
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
