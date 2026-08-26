"""Formatação de números no padrão brasileiro.

Regra da casa: todo valor monetário aparece em reais COM centavos,
tanto na tela quanto na exportação.
"""

from decimal import Decimal, InvalidOperation

CEM = Decimal("100")


def para_decimal(valor) -> Decimal:
    """Converte texto do CSV ('1.234.567,89') em Decimal.

    Aceita número já pronto, vazio, '-' e parênteses de negativo.
    """
    if valor is None:
        return Decimal("0")
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, (int, float)):
        return Decimal(str(valor))

    texto = str(valor).strip()
    if texto in ("", "-", "--"):
        return Decimal("0")

    negativo = texto.startswith("(") and texto.endswith(")")
    texto = texto.strip("()").replace(" ", "").replace(".", "").replace(",", ".")

    try:
        numero = Decimal(texto)
    except InvalidOperation:
        return Decimal("0")

    return -numero if negativo else numero


def reais(valor, com_simbolo: bool = True) -> str:
    """1234567.89 -> 'R$ 1.234.567,89'"""
    numero = para_decimal(valor).quantize(Decimal("0.01"))
    negativo = numero < 0
    inteiro, centavos = f"{abs(numero):.2f}".split(".")

    grupos = []
    while len(inteiro) > 3:
        grupos.insert(0, inteiro[-3:])
        inteiro = inteiro[:-3]
    grupos.insert(0, inteiro)

    texto = ".".join(grupos) + "," + centavos
    if negativo:
        texto = "-" + texto
    return f"R$ {texto}" if com_simbolo else texto


def resumido(valor) -> str:
    """Versão curta para cards: 'R$ 146,97 bi'."""
    numero = para_decimal(valor)
    sinal = "-" if numero < 0 else ""
    n = abs(numero)

    for limite, sufixo in (
        (Decimal("1000000000"), "bi"),
        (Decimal("1000000"), "mi"),
        (Decimal("1000"), "mil"),
    ):
        if n >= limite:
            reduzido = (n / limite).quantize(Decimal("0.01"))
            return f"{sinal}R$ {str(reduzido).replace('.', ',')} {sufixo}"
    return reais(numero)


def resumido_quantidade(valor) -> str:
    """Versão curta para contagens: '659.445' ou '1,2 mi' — sem 'R$'.

    Pessoal, cargos e obras são contagens, não dinheiro. Formatá-las com
    `resumido()` produzia coisas como "R$ 659,44 mil" para 659.445 cargos.
    """
    numero = para_decimal(valor)
    sinal = "-" if numero < 0 else ""
    n = abs(numero)

    if n >= Decimal("1000000"):
        reduzido = (n / Decimal("1000000")).quantize(Decimal("0.01"))
        return f"{sinal}{str(reduzido).replace('.', ',')} mi"
    return sinal + inteiro(n)


def resumo_por_tipo(valor, tipo: str) -> tuple[str, str]:
    """Devolve (destaque, detalhe) conforme o tipo da coluna."""
    if tipo == "quantidade":
        return resumido_quantidade(valor), ""
    return resumido(valor), reais(valor)


def inteiro(valor) -> str:
    """1605 -> '1.605' (quantidades, sem centavos)."""
    return reais(valor, com_simbolo=False).split(",")[0]


def percentual(parte, total, casas: int = 2) -> str:
    """Participação percentual de `parte` sobre `total`."""
    total = para_decimal(total)
    if total == 0:
        return "0,00%"
    valor = (para_decimal(parte) / total * CEM).quantize(Decimal("0.01"))
    return f"{valor:.{casas}f}".replace(".", ",") + "%"


FORMATADORES = {
    "texto": lambda v: "" if v is None else str(v),
    "dinheiro": lambda v: reais(v, com_simbolo=False),
    "quantidade": inteiro,
    "percentual": lambda v: f"{para_decimal(v):.2f}".replace(".", ",") + "%",
}


def formatar(valor, tipo: str) -> str:
    """Aplica o formatador declarado na coluna do config."""
    return FORMATADORES.get(tipo, FORMATADORES["texto"])(valor)
