"""Mapa interativo de Minas Gerais por município.

O mapa é renderizado no navegador a partir da malha municipal do IBGE.
Os valores financeiros são embutidos no HTML durante o `loa build`, então o
site não depende de uma API financeira em produção. A única requisição feita
pelo navegador é para a malha geográfica pública do IBGE.
"""

import html
import json
import re
import unicodedata
from decimal import Decimal
from pathlib import Path

from ..dados import ler
from ..formato import para_decimal, percentual, resumido

ESCALA = ["#f7eeee", "#f0caca", "#e7a0a0", "#d96b6b", "#b83d3d", "#7f1717"]


def chave(nome: str) -> str:
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", str(nome))
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", sem_acento.upper()).strip()


def slug(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", chave(texto).lower()).strip("-")


def _agregar_municipios(linhas, campo_nome="municipio", campo_valor="total"):
    totais: dict[str, Decimal] = {}
    nomes: dict[str, str] = {}
    for linha in linhas:
        nome = str(linha.get(campo_nome, "")).strip()
        k = chave(nome)
        # "Diversos Municípios - ..." e "Estadual" não possuem polígono
        # municipal e, portanto, não entram no mapa.
        if not k or "DIVERSOS MUNICIPIOS" in k or k == "ESTADUAL":
            continue
        totais[k] = totais.get(k, Decimal(0)) + para_decimal(linha.get(campo_valor))
        nomes.setdefault(k, nome)
    return totais, nomes


def montar(linhas, config, pasta_dados: Path) -> str:
    """Gera o contêiner do mapa municipal."""
    tipo = config.get("tipo", "municipios")
    if tipo != "municipios":
        return ""

    arquivo = pasta_dados / config.get("dados", "obras_municipio.csv")
    if not arquivo.exists():
        return ""

    registros = ler(pasta_dados, arquivo.name)
    campo_nome = config.get("campo_nome", "municipio")
    campo_valor = config.get("campo_valor", "total")
    totais, nomes = _agregar_municipios(registros, campo_nome, campo_valor)
    if not totais:
        return ""

    total = sum(totais.values(), Decimal(0))
    dados = []
    for k, valor in sorted(totais.items(), key=lambda item: -item[1]):
        nome = nomes[k]
        dados.append({
            "id": slug(nome),
            "nome": nome,
            "chave": k,
            "valor": float(valor),
            "valorFormatado": resumido(valor),
            "percentual": percentual(valor, total),
            "href": f"{config.get('href_base', '../obras-municipio/municipio-')}{slug(nome)}/",
        })

    return (
        '<figure class="loa-figura loa-figura--mapa loa-figura--mapa-municipios">'
        f'<figcaption>{html.escape(config.get("titulo", "Investimento previsto por município"))}</figcaption>'
        '<div class="loa-mapa-municipios" '
        'data-geojson-url="https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-31-mun.json" '
        f'data-map-data="{html.escape(json.dumps(dados, ensure_ascii=False, separators=(",", ":")))}" '
        'data-geojson-fallback="https://servicodados.ibge.gov.br/api/v4/malhas/estados/31?formato=application/vnd.geo%2Bjson&amp;resolucao=2&amp;intrarregiao=municipio" '
        'role="img" aria-label="Mapa de Minas Gerais com investimentos previstos por município">'
        '<div class="loa-mapa-municipios__status">Carregando mapa de Minas Gerais…</div>'
        '</div>'
        '<div class="loa-legenda loa-legenda--mapa-municipios">'
        '<span>sem investimento localizado</span>'
        + "".join(f'<i style="background:{cor}"></i>' for cor in ESCALA)
        + '<span>maior investimento</span>'
        '</div>'
        '<p class="loa-figura__nota">Os municípios sem investimento localizado aparecem em cinza. '
        'Passe o mouse para consultar os valores e clique em um município com investimento para abrir o detalhamento.</p>'
        '</figure>'
    )
