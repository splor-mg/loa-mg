"""Cards de resumo — a primeira coisa que o cidadão vê na página.

No YAML:

    cards:
      - titulo: Despesa total do Estado
        campo: total
        funcao: soma          # soma | contagem | maximo | valor_de
        nota: Orçamento Fiscal 2026
"""

from decimal import Decimal

from ..dados import filtrar, somar
from ..formato import inteiro, resumo_por_tipo


def _tipo_do_card(card: dict, colunas: list[dict]) -> str:
    """Descobre se o card mostra dinheiro ou contagem.

    Prioridade: o que o YAML declarar em `tipo`; senão, o tipo da coluna
    que o card soma. Sem isto, um card sobre número de servidores saía
    formatado como reais.
    """
    if card.get("tipo"):
        return card["tipo"]
    campo = card.get("campo")
    for coluna in colunas or []:
        if coluna.get("campo") == campo:
            return coluna.get("tipo", "dinheiro")
    return "dinheiro"


def _calcular(linhas: list[dict], card: dict):
    funcao = card.get("funcao", "soma")
    campo = card.get("campo")
    selecionadas = filtrar(linhas, card.get("filtro", {}))

    if funcao == "contagem":
        return len(selecionadas), "quantidade"
    if funcao == "soma":
        return somar(selecionadas, campo), "dinheiro"
    if funcao == "maximo":
        from ..formato import para_decimal
        valores = [para_decimal(l.get(campo)) for l in selecionadas] or [Decimal(0)]
        return max(valores), "dinheiro"
    if funcao == "valor_de":
        return (selecionadas[0].get(campo) if selecionadas else 0), "dinheiro"

    raise ValueError(f"Função de card desconhecida: {funcao}")


def montar(linhas: list[dict], config_cards: list[dict], colunas: list[dict] | None = None) -> str:
    """Gera o HTML da faixa de cards."""
    if not config_cards:
        return ""

    pecas = ['<div class="loa-cards">']
    for card in config_cards:
        valor, tipo = _calcular(linhas, card)
        if tipo != "quantidade":
            tipo = _tipo_do_card(card, colunas)

        grande, detalhe = resumo_por_tipo(valor, tipo)

        pecas.append('<div class="loa-card">')
        pecas.append(f'<span class="loa-card__titulo">{card["titulo"]}</span>')
        pecas.append(f'<strong class="loa-card__valor">{grande}</strong>')
        if detalhe:
            pecas.append(f'<span class="loa-card__exato">{detalhe}</span>')
        if card.get("nota"):
            pecas.append(f'<span class="loa-card__nota">{card["nota"]}</span>')
        pecas.append("</div>")
    pecas.append("</div>")
    return "\n".join(pecas)
