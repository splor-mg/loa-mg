"""Validações de consistência.

Este é o argumento mais forte do projeto: ninguém confere à mão se as
1.793 páginas do PDF fecham. Aqui, se não fechar, o build acusa.

Tipos disponíveis no YAML:

    validacoes:
      - {tipo: soma_igual, campo: total, esperado: 146969637358.00}
      - {tipo: soma_por_grupo, campo: total, grupo: orgao_nome, comparar_com: ...}
      - {tipo: colunas_somam, parcelas: [a, b, c], total: total}
      - {tipo: sem_vazios, campos: [uo_nome, valor]}
      - {tipo: niveis_fecham, campo_nivel: nivel, campo: total}
"""

from dataclasses import dataclass
from decimal import Decimal

from .dados import somar
from .formato import para_decimal, reais

TOLERANCIA = Decimal("0.01")


@dataclass
class Resultado:
    demonstrativo: str
    descricao: str
    ok: bool
    detalhe: str = ""

    def __str__(self) -> str:
        marca = "OK  " if self.ok else "FALHA"
        base = f"  [{marca}] {self.demonstrativo}: {self.descricao}"
        return base if self.ok else f"{base}\n          {self.detalhe}"


def _soma_igual(linhas, regra):
    obtido = somar(linhas, regra["campo"])
    esperado = para_decimal(regra["esperado"])
    diferenca = abs(obtido - esperado)
    return (
        diferenca <= TOLERANCIA,
        f"soma de '{regra['campo']}' = {reais(obtido)}, "
        f"esperado {reais(esperado)} (diferença {reais(diferenca)})",
    )


def _colunas_somam(linhas, regra):
    problemas = []
    for i, linha in enumerate(linhas, start=2):
        parcelas = sum(
            (para_decimal(linha.get(c)) for c in regra["parcelas"]), start=Decimal(0)
        )
        total = para_decimal(linha.get(regra["total"]))
        if abs(parcelas - total) > TOLERANCIA:
            rotulo = next(iter(linha.values()))
            problemas.append(f"linha {i} ({rotulo}): {reais(parcelas)} != {reais(total)}")
    return (
        not problemas,
        f"{len(problemas)} linha(s) não fecham: " + "; ".join(problemas[:5]),
    )


def _sem_vazios(linhas, regra):
    problemas = [
        f"linha {i} sem '{campo}'"
        for i, linha in enumerate(linhas, start=2)
        for campo in regra["campos"]
        if not str(linha.get(campo, "")).strip()
    ]
    return not problemas, f"{len(problemas)} célula(s) vazias: " + "; ".join(problemas[:5])


def _niveis_fecham(linhas, regra):
    """Cada linha-pai deve ser igual à soma dos seus filhos imediatos.

    "Filho imediato" é o nível mais raso encontrado dentro do bloco de
    descendentes — e não necessariamente `nivel + 1`. Os códigos
    orçamentários pulam níveis quando um segmento fica zerado, e isso é
    normal, não erro.
    """
    campo_nivel, campo = regra["campo_nivel"], regra["campo"]
    problemas = []

    for i, linha in enumerate(linhas):
        nivel = int(linha.get(campo_nivel) or 0)

        bloco = []
        for proxima in linhas[i + 1:]:
            n = int(proxima.get(campo_nivel) or 0)
            if n <= nivel:
                break
            bloco.append((n, proxima))
        if not bloco:
            continue

        nivel_filho = min(n for n, _ in bloco)
        filhos = sum(
            (para_decimal(p.get(campo)) for n, p in bloco if n == nivel_filho),
            start=Decimal(0),
        )
        if filhos == 0:
            continue

        pai = para_decimal(linha.get(campo))
        if abs(pai - filhos) > TOLERANCIA:
            rotulo = next(iter(linha.values()))
            problemas.append(f"'{rotulo}': pai {reais(pai)} vs filhos {reais(filhos)}")

    return (
        not problemas,
        f"{len(problemas)} hierarquia(s) não fecham: " + "; ".join(problemas[:5]),
    )


def _parcelas_somam_total(linhas, regra):
    """A soma das parcelas é igual à linha de total declarada no arquivo.

    Muitos demonstrativos trazem, na mesma coluna, as parcelas e a linha
    que as totaliza. Somar tudo conta o mesmo dinheiro duas vezes — foi o
    que aconteceu no Resumo por Categorias Econômicas, que exibia
    R$ 249 bi de receita onde o correto eram R$ 127 bi.

    A importação separa os dois com a coluna `papel`; esta regra confere
    que a separação está certa e que nenhuma parcela se perdeu no caminho.
    Quando `agrupar_por` é informado, a conferência é feita grupo a grupo.
    """
    campo = regra["campo"]
    papel = regra.get("campo_papel", "papel")
    grupos = regra.get("agrupar_por")
    if isinstance(grupos, str):
        grupos = [grupos]

    def chave(linha):
        return tuple(linha.get(g, "") for g in grupos) if grupos else ()

    parcelas: dict = {}
    totais: dict = {}
    for linha in linhas:
        destino = parcelas if linha.get(papel) == "parcela" else (
            totais if linha.get(papel) == "total" else None)
        if destino is None:
            continue          # 'resultado' (déficit) fica de fora
        k = chave(linha)
        destino[k] = destino.get(k, Decimal(0)) + para_decimal(linha.get(campo))

    problemas = []
    for k in sorted(set(parcelas) | set(totais), key=str):
        soma = parcelas.get(k, Decimal(0))
        alvo = totais.get(k, Decimal(0))
        if alvo == 0 and soma == 0:
            continue
        if abs(soma - alvo) > TOLERANCIA:
            rotulo = " / ".join(str(x) for x in k) if k else "total geral"
            problemas.append(f"{rotulo}: parcelas {reais(soma)} vs total {reais(alvo)}")

    return (
        not problemas,
        f"{len(problemas)} grupo(s) não fecham: " + "; ".join(problemas[:5]),
    )


REGRAS = {
    "parcelas_somam_total": _parcelas_somam_total,
    "soma_igual": _soma_igual,
    "colunas_somam": _colunas_somam,
    "sem_vazios": _sem_vazios,
    "niveis_fecham": _niveis_fecham,
}


def verificar(nome_demonstrativo: str, linhas: list[dict], regras: list[dict]) -> list[Resultado]:
    from .dados import filtrar

    resultados = []
    for regra in regras or []:
        # uma regra pode se aplicar só a parte das linhas
        alvo = filtrar(linhas, regra.get("filtro", {}))
        funcao = REGRAS.get(regra["tipo"])
        if not funcao:
            resultados.append(
                Resultado(nome_demonstrativo, regra["tipo"], False, "tipo de validação desconhecido")
            )
            continue
        ok, detalhe = funcao(alvo, regra)
        resultados.append(
            Resultado(nome_demonstrativo, regra.get("descricao", regra["tipo"]), ok, detalhe)
        )
    return resultados
