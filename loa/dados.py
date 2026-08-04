"""Leitura dos dados.

Convenção da casa: CSV com separador ';', decimal ',', codificação UTF-8.
Arquivos .csv.gz também são aceitos (o servidor de dados envia compactado).

Nenhuma tabela auxiliar: toda hierarquia sai dos próprios dados.
"""

import csv
import gzip
from pathlib import Path

from .formato import para_decimal

_CACHE: dict[str, list[dict]] = {}


def caminho(pasta_dados: Path, nome: str) -> Path:
    """Aceita 'x.csv' e encontra 'x.csv' ou 'x.csv.gz'."""
    direto = pasta_dados / nome
    if direto.exists():
        return direto
    comprimido = pasta_dados / (nome + ".gz")
    if comprimido.exists():
        return comprimido
    raise FileNotFoundError(
        f"Arquivo de dados não encontrado: {direto} (nem .gz).\n"
        f"Confira o campo 'dados:' em config/demonstrativos.yml."
    )


def ler(pasta_dados: Path, nome: str) -> list[dict]:
    """Lê um CSV e devolve lista de dicionários. O resultado fica em cache."""
    if nome in _CACHE:
        return _CACHE[nome]

    arquivo = caminho(pasta_dados, nome)
    abrir = gzip.open if arquivo.suffix == ".gz" else open

    with abrir(arquivo, "rt", encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f, delimiter=";"))

    _CACHE[nome] = linhas
    return linhas


def filtrar(linhas: list[dict], filtros: dict) -> list[dict]:
    """Mantém só as linhas em que campo == valor (comparação como texto)."""
    if not filtros:
        return linhas
    return [
        linha
        for linha in linhas
        if all(str(linha.get(c, "")) == str(v) for c, v in filtros.items())
    ]


def valores_distintos(linhas: list[dict], campo: str) -> list[str]:
    """Valores únicos de uma coluna, preservando a ordem de aparição."""
    vistos, resultado = set(), []
    for linha in linhas:
        v = linha.get(campo, "")
        if v not in vistos:
            vistos.add(v)
            resultado.append(v)
    return resultado


def somar(linhas: list[dict], campo: str):
    """Soma uma coluna monetária."""
    total = para_decimal(0)
    for linha in linhas:
        total += para_decimal(linha.get(campo))
    return total


def ordenar(linhas: list[dict], campo: str, desc: bool = True) -> list[dict]:
    """Ordena por uma coluna. Numérica se der, senão alfabética."""
    def chave(linha):
        bruto = linha.get(campo, "")
        numero = para_decimal(bruto)
        if numero != 0 or str(bruto).strip() in ("0", "0,00", ""):
            return (0, numero)
        return (1, str(bruto))

    try:
        return sorted(linhas, key=lambda l: para_decimal(l.get(campo)), reverse=desc)
    except Exception:
        return sorted(linhas, key=lambda l: str(l.get(campo, "")), reverse=desc)


def limpar_cache() -> None:
    _CACHE.clear()
