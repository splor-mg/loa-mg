"""Mapa das regiões geográficas intermediárias de Minas Gerais.

O Anexo IV — 133 páginas de tabelinhas por região — é o caso mais óbvio
de ganho visual do projeto inteiro. Aqui ele vira um mapa clicável.

Duas formas de desenhar:

1. Se existir `dados/regioes-mg.geojson`, desenha o mapa geográfico de
   verdade (basta baixar o shapefile do IBGE e converter uma vez).
2. Se não existir, desenha um "mapa de blocos": cada região é um
   quadrado posicionado mais ou menos onde ela fica no estado. Fica
   legível, imprime bem e não depende de nenhum arquivo externo.

Em ambos os casos a cor representa o valor e o clique leva para a
tabela completa daquela região — nenhum dado se perde.
"""

import html
import json
import re
import unicodedata
from decimal import Decimal
from pathlib import Path

from ..formato import para_decimal, percentual, resumido

# Posição aproximada de cada região no estado (coluna, linha).
# Ajuste livre: é só mudar os números abaixo.
BLOCOS = {
    "PATOS DE MINAS": (1, 0),
    "MONTES CLAROS": (2, 0),
    "TEOFILO OTONI": (4, 0),
    "UBERLANDIA": (0, 1),
    "GOVERNADOR VALADARES": (4, 1),
    "UBERABA": (0, 2),
    "DIVINOPOLIS": (1, 2),
    "BELO HORIZONTE": (2, 2),
    "IPATINGA": (3, 2),
    "VARGINHA": (1, 3),
    "BARBACENA": (2, 3),
    "JUIZ DE FORA": (3, 3),
    "POUSO ALEGRE": (1, 4),
}

# Seis faixas, do menor ao maior investimento.
ESCALA = ["#fcebeb", "#f7c1c1", "#f09595", "#e24b4a", "#a32d2d", "#501313"]


def chave(nome: str) -> str:
    """Normaliza o nome da região para casar com o dicionário acima."""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", str(nome)) if unicodedata.category(c) != "Mn"
    )
    sem_acento = re.sub(r"REGI[AÃ]O\s+INTERMEDI[AÁ]RIA\s+DE\s+", "", sem_acento.upper())
    return re.sub(r"\s+", " ", sem_acento).strip()


def _escala_por_posicao(valores: list[Decimal]) -> dict:
    """Mapeia cada valor a uma faixa de cor pela sua POSIÇÃO no ranking.

    A alternativa — dividir pelo maior — não funciona aqui: em Minas, Belo
    Horizonte investe mais que o dobro da segunda colocada, e uma escala
    linear jogaria as outras doze regiões todas no tom mais claro. O mapa
    ficaria pálido e não diria nada.

    Ordenando por posição, as seis faixas são todas usadas. A legenda diz
    "menor → maior investimento", que é exatamente o que a cor representa;
    o valor exato e o percentual continuam escritos dentro de cada bloco.
    """
    ordenados = sorted(set(valores))
    if not ordenados:
        return {}
    if len(ordenados) == 1:
        return {ordenados[0]: len(ESCALA) - 1}
    return {
        valor: min(int(i / (len(ordenados) - 1) * (len(ESCALA) - 1)), len(ESCALA) - 1)
        for i, valor in enumerate(ordenados)
    }


def _cor(valor: Decimal, escala: dict) -> str:
    return ESCALA[escala.get(valor, 0)]


def _agregar(linhas, campo_regiao, campo_valor):
    totais: dict[str, Decimal] = {}
    nomes: dict[str, str] = {}
    for linha in linhas:
        k = chave(linha.get(campo_regiao, ""))
        if not k:
            continue
        totais[k] = totais.get(k, Decimal(0)) + para_decimal(linha.get(campo_valor))
        nomes.setdefault(k, str(linha.get(campo_regiao, "")).strip())
    return totais, nomes


def _mapa_geojson(arquivo: Path, totais, nomes, campo_nome_geo: str) -> str:
    """Desenha o mapa real a partir de um GeoJSON de regiões."""
    geo = json.loads(arquivo.read_text(encoding="utf-8"))
    escala = _escala_por_posicao([v for k, v in totais.items() if k in BLOCOS]
                                 or list(totais.values()))

    xs, ys = [], []

    def pontos(coords):
        for anel in coords:
            for x, y in anel:
                xs.append(x)
                ys.append(y)

    for feicao in geo["features"]:
        g = feicao["geometry"]
        if g["type"] == "Polygon":
            pontos(g["coordinates"])
        else:
            for parte in g["coordinates"]:
                pontos(parte)

    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    larg, alt = 900, 620

    def proj(x, y):
        px = (x - minx) / (maxx - minx) * (larg - 40) + 20
        py = alt - ((y - miny) / (maxy - miny) * (alt - 40) + 20)
        return f"{px:.1f},{py:.1f}"

    partes = [f'<svg class="loa-mapa" viewBox="0 0 {larg} {alt}" role="img" '
              f'aria-label="Mapa de investimentos por região de Minas Gerais">']
    for feicao in geo["features"]:
        nome = feicao["properties"].get(campo_nome_geo, "")
        k = chave(nome)
        valor = totais.get(k, Decimal(0))
        g = feicao["geometry"]
        aneis = g["coordinates"] if g["type"] == "Polygon" else [a for p in g["coordinates"] for a in p]
        d = " ".join(
            "M " + " L ".join(proj(x, y) for x, y in anel) + " Z" for anel in aneis
        )
        partes.append(
            f'<path d="{d}" fill="{_cor(valor, escala)}" stroke="#ffffff" '
            f'stroke-width="1.2" class="loa-mapa__area" role="link" tabindex="0" '
            f'data-href="regiao-{_slug(k)}/">'
            f"<title>{html.escape(nomes.get(k, nome))}: {resumido(valor)}</title></path>"
        )
    partes.append("</svg>")
    return "".join(partes)


def _mapa_blocos(totais, nomes) -> str:
    """Mapa de blocos em HTML puro (grade CSS), não em SVG.

    Por que HTML e não SVG: um `<a>` dentro de um SVG vira um SVGAElement,
    cuja propriedade `href` é somente leitura. A navegação instantânea do
    MkDocs Material percorre os links da página nova e reescreve `a.href`
    para normalizar as URLs — ao esbarrar num link de SVG ela lança
    TypeError, o carregamento morre no meio e a página não troca.

    Como os blocos são retângulos, HTML faz o mesmo trabalho, com links de
    verdade, layout responsivo de graça e melhor comportamento na impressão.
    """
    mapeados = [v for k, v in totais.items() if k in BLOCOS]
    escala = _escala_por_posicao(mapeados)
    total_geral = sum(totais.values(), start=Decimal(0))

    celulas = []
    for chave_bloco, (coluna, linha) in BLOCOS.items():
        valor = totais.get(chave_bloco, Decimal(0))
        nome = nomes.get(chave_bloco, chave_bloco.title())
        curto = re.sub(r"REGIÃO INTERMEDIÁRIA DE ", "", nome, flags=re.I)
        faixa = escala.get(valor, 0)
        classe_texto = "loa-bloco--escuro" if faixa >= 3 else "loa-bloco--claro"

        celulas.append(
            f'<a class="loa-bloco {classe_texto}" href="regiao-{_slug(chave_bloco)}/" '
            f'style="--coluna:{coluna + 1};--linha:{linha + 1};'
            f'--cor:{ESCALA[faixa]}" '
            f'title="{html.escape(nome)}: {resumido(valor)}">'
            f'<span class="loa-bloco__nome">{html.escape(curto.title())}</span>'
            f'<span class="loa-bloco__valor">{resumido(valor)}</span>'
            f'<span class="loa-bloco__parte">{percentual(valor, total_geral)}</span>'
            f"</a>"
        )

    return f'<div class="loa-blocos">{"".join(celulas)}</div>'


def _slug(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", chave(texto).lower()).strip("-")


def montar(linhas, config, pasta_dados: Path) -> str:
    """Gera o bloco do mapa a partir do YAML."""
    totais, nomes = _agregar(linhas, config["regiao"], config["valor"])
    if not totais:
        return ""

    geojson = pasta_dados / config.get("geojson", "regioes-mg.geojson")
    if geojson.exists():
        svg = _mapa_geojson(geojson, totais, nomes, config.get("campo_geojson", "NM_RGINT"))
        aviso = ""
    else:
        svg = _mapa_blocos(totais, nomes)
        aviso = (
            '<p class="loa-figura__nota">Cada bloco é uma região geográfica '
            "intermediária, posicionada aproximadamente onde ela fica no estado. "
            "Clique para ver a tabela completa da região. Para exibir o mapa "
            "geográfico, coloque o arquivo <code>regioes-mg.geojson</code> na "
            "pasta <code>dados/</code>.</p>"
        )

    legenda = "".join(
        f'<span class="loa-legenda__item"><i style="background:{c}"></i></span>' for c in ESCALA
    )

    # Territórios sem bloco no mapa entram na tabela, mas precisam ser
    # declarados aqui para o leitor não achar que o mapa esconde dinheiro.
    fora = [(nomes.get(k, k), v) for k, v in totais.items() if k not in BLOCOS]
    nota_fora = ""
    if fora:
        itens = "; ".join(
            f"{nome} — {resumido(valor)} ({percentual(valor, sum(totais.values(), start=Decimal(0)))})"
            for nome, valor in sorted(fora, key=lambda x: -x[1])
        )
        nota_fora = (
            f'<p class="loa-figura__nota"><strong>Fora do mapa:</strong> {itens}. '
            "São obras sem localização em uma região só — uma rodovia que cruza "
            "várias, um sistema estadual, uma frota. O valor está na tabela abaixo "
            "e no ranking, mas não cabe em um bloco.</p>"
        )

    return (
        f'<figure class="loa-figura loa-figura--mapa">'
        f'<figcaption>{html.escape(config["titulo"])}</figcaption>'
        f"{svg}"
        f'<div class="loa-legenda"><span>menor investimento</span>{legenda}'
        f"<span>maior investimento</span></div>{nota_fora}{aviso}</figure>"
    )
