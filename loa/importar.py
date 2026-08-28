"""Importação dos dados brutos da LOA.

Os sete volumes que a SPLOR usa para gerar os PDFs vêm em arquivos TSV
(separados por tabulação), com valores em reais inteiros e separador de
milhar por ponto. Este módulo os converte para o padrão do projeto:
CSV com `;`, decimal `,` e centavos.

Uso:

    poetry run loa importar ~/Downloads/arquivos_data

Rode de novo sempre que o datapackage for atualizado. Nada é digitado à
mão: se um número mudar na origem, ele muda no site.

Mapa dos volumes:

    1  Anexo I    demonstrativos consolidados (T1 a T39)
    2  Anexo II   orçamento fiscal, 5 tabelas por unidade orçamentária
    3  Anexo III  investimento das empresas controladas
    4  Anexo IV   distribuição regionalizada e obras por município
    5  QDD        quadro de detalhamento da despesa
    6  QDD        idem, com receita por fonte
    7  QDD        idem, com sequencial de iniciativa
"""

import csv
import re
import unicodedata
from pathlib import Path

CENTAVOS = ",00"


# --------------------------------------------------------------------------
# leitura dos arquivos brutos
# --------------------------------------------------------------------------

def _texto(valor: str) -> str:
    """Tira aspas, espaços sobrando e normaliza o espaçamento interno."""
    return re.sub(r"\s+", " ", str(valor or "").strip().strip('"')).strip()


def _numero(valor: str) -> str:
    """'1.234.567' -> '1234567,00'. Vazio, '-' e '0' viram '0,00'."""
    bruto = _texto(valor)
    if not bruto or bruto in ("-", "--"):
        return ""
    negativo = bruto.startswith("(") and bruto.endswith(")") or bruto.startswith("-")
    digitos = re.sub(r"[^\d]", "", bruto)
    if not digitos:
        return ""
    return ("-" if negativo else "") + str(int(digitos)) + CENTAVOS


def _percentual(valor: str) -> str:
    """Normaliza percentuais da origem para o formato exibido pelo site."""
    bruto = _texto(valor).replace("%", "")
    if not bruto:
        return ""
    try:
        numero = float(bruto.replace(".", "").replace(",", "."))
    except ValueError:
        return ""
    return f"{numero:.2f}".replace(".", ",") + "%"


def ler_tsv(caminho: Path, bruto: bool = False) -> list[dict]:
    """Lê um arquivo do datapackage. Aceita tabulação ou ponto-e-vírgula.

    Com `bruto=True` os valores saem sem limpeza de espaços. Alguns arquivos
    foram formatados para impressão e usam o RECUO do texto para indicar a
    hierarquia — normalizar destruiria essa informação.
    """
    conteudo = caminho.read_text(encoding="utf-8-sig", errors="replace")
    separador = ";" if conteudo.count(";") > conteudo.count("\t") else "\t"
    linhas = list(csv.DictReader(conteudo.splitlines(), delimiter=separador))
    if bruto:
        return [{_texto(k): (v or "") for k, v in linha.items() if k} for linha in linhas]
    return [{_texto(k): _texto(v) for k, v in linha.items() if k} for linha in linhas]


def ler_pasta(pasta: Path) -> list[dict]:
    """Lê todos os .txt de uma pasta (uma por unidade orçamentária)."""
    registros = []
    for arquivo in sorted(pasta.glob("*.txt")):
        registros += ler_tsv(arquivo)
    return registros


def preencher(registros: list[dict], campos: list[str]) -> list[dict]:
    """Repete para baixo o valor de campos que só aparecem na primeira linha.

    Os arquivos vêm formatados para impressão: o nome do órgão e da unidade
    aparecem uma vez e ficam em branco nas linhas seguintes.
    """
    ultimo: dict[str, str] = {}
    for registro in registros:
        for campo in campos:
            if registro.get(campo):
                ultimo[campo] = registro[campo]
            elif campo in ultimo:
                registro[campo] = ultimo[campo]
    return registros


def gravar(destino: Path, nome: str, colunas: list[str], linhas: list[list]) -> int:
    destino.mkdir(parents=True, exist_ok=True)
    with open(destino / nome, "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f, delimiter=";")
        escritor.writerow(colunas)
        escritor.writerows(linhas)
    return len(linhas)


# --------------------------------------------------------------------------
# hierarquia da classificação orçamentária
# --------------------------------------------------------------------------

def nivel_do_codigo(codigo: str) -> int:
    """Profundidade do código de receita (1000.00.0.0.00.000).

    O código é posicional: cada dígito dos quatro primeiros e cada segmento
    seguinte é um nível. Vale a posição do ÚLTIMO segmento preenchido — parar
    no primeiro zero colapsaria níveis distintos, porque 1321.01.0.1.00.000
    tem o quarto segmento preenchido mesmo com o terceiro zerado.
    """
    partes = _texto(codigo).split(".")
    if not partes or not partes[0].isdigit():
        return 1
    posicoes = list(partes[0]) + partes[1:]
    ultimo = 0
    for i, parte in enumerate(posicoes, start=1):
        if parte.strip("0"):
            ultimo = i
    return max(ultimo, 1)


MINUSCULAS = {"de", "do", "da", "dos", "das", "e", "em", "a", "o", "no", "na"}


def titulo(texto: str) -> str:
    """'JUÍZ DE FORA' -> 'Juíz de Fora' (preposições em minúscula)."""
    palavras = []
    for i, palavra in enumerate(_texto(texto).split()):
        minuscula = palavra.lower()
        palavras.append(minuscula if i > 0 and minuscula in MINUSCULAS
                        else palavra.capitalize())
    return " ".join(palavras)


def so_uo(nome: str) -> str:
    """'1.26.1 - SECRETARIA DE ESTADO DE EDUCAÇÃO - SEE' -> nome sem o código."""
    limpo = _texto(nome)
    return re.sub(r"^[\d\.]+\s*-\s*", "", limpo)


def codigo_de(nome: str) -> str:
    achado = re.match(r"^([\d\.]+)\s*-\s*", _texto(nome))
    return achado.group(1) if achado else ""


# --------------------------------------------------------------------------
# Volume 1 — Anexo I
# --------------------------------------------------------------------------

def importar_anexo_i(volume: Path, destino: Path) -> dict[str, int]:
    resultado = {}

    # T1: receita e despesa lado a lado, com colunas ordinária/vinculada/total
    t1 = volume / "T1_DEMONSTRATIVO_CONSOLIDADO_ORCAMENTO_FISCAL.csv"
    if t1.exists():
        registros_t1 = ler_tsv(t1, bruto=True)

        # Descobre os recuos que o arquivo usa e os mapeia em níveis 1, 2, 3…
        recuos = set()
        for registro in registros_t1:
            for campo in ("receita", "despesa"):
                bruto = registro.get(campo, "")
                if bruto.strip():
                    recuos.add(len(bruto) - len(bruto.lstrip()))
        escada = {recuo: i for i, recuo in enumerate(sorted(recuos), start=1)}

        linhas = []
        for registro in registros_t1:
            for lado, prefixo in (("receita", "_rec"), ("despesa", "")):
                rotulo_bruto = registro.get("receita" if lado == "receita" else "despesa", "")
                rotulo = _texto(rotulo_bruto)
                if not rotulo:
                    continue
                # o recuo do arquivo original marca a hierarquia
                recuo = len(rotulo_bruto) - len(rotulo_bruto.lstrip())
                nivel = escada.get(recuo, 1)
                if rotulo.upper().startswith("TOTAL"):
                    nivel = 1
                ordinaria = _numero(registro.get(f"ordinaria{prefixo}"))
                vinculada = _numero(registro.get(f"vinculada{prefixo}"))
                total = _numero(registro.get(f"total{prefixo}"))
                if not total:
                    continue
                part_ord = _percentual(registro.get(f"part_ord{prefixo}"))
                part_vinc = _percentual(registro.get(f"part_vinc{prefixo}"))
                part_total = _percentual(registro.get(f"part_total{prefixo}"))
                if lado == "receita":
                    linhas.append([lado, nivel, rotulo, ordinaria or "0,00", part_ord,
                                   vinculada or "0,00", part_vinc, total, part_total, "", "", ""])
                else:
                    linhas.append([lado, nivel, rotulo, ordinaria or "0,00", "",
                                   vinculada or "0,00", "", total, "", part_ord, part_vinc, part_total])
        resultado["consolidado_fiscal.csv"] = gravar(
            destino, "consolidado_fiscal.csv",
            ["lado", "nivel", "especificacao", "ordinaria", "part_ord_rec",
             "vinculada", "part_vinc_rec", "total", "part_total_rec",
             "part_ord", "part_vinc", "part_total"], linhas)

    # T3: resumo por categoria econômica.
    #
    # O arquivo mistura três coisas na mesma coluna: as PARCELAS (receitas
    # correntes, de capital…), a linha TOTAL e a linha DÉFICIT. Somar tudo
    # conta o mesmo dinheiro três vezes — a coluna `papel` separa os três.
    t3 = volume / "T3_DCGF_Resumo_Demonst_Receita_Despesa_Segundo_Categorias.txt"
    if t3.exists():
        linhas = []
        for registro in ler_tsv(t3):
            for lado, campo_nome, campo_valor in (
                ("receita", "RECEITA_DESC", "vl_rec_total"),
                ("despesa", "DESPESA_DESC", "vl_desp_total"),
            ):
                nome = _texto(registro.get(campo_nome))
                valor = _numero(registro.get(campo_valor))
                if not (nome and valor):
                    continue
                acima = nome.upper()
                if acima.startswith("TOTAL"):
                    papel = "total"
                elif acima.startswith(("DÉFICIT", "DEFICIT", "SUPERÁVIT", "SUPERAVIT")):
                    papel = "resultado"
                else:
                    papel = "parcela"
                linhas.append([lado, papel, nome, valor])
        resultado["categorias_economicas.csv"] = gravar(
            destino, "categorias_economicas.csv",
            ["lado", "papel", "especificacao", "valor"], linhas)

    # T4: despesa por unidade orçamentária e grupo
    t4 = volume / "T4_DEMONSTRATIVO_DESPESA_POR_ORGAOS_ENTIDADES_SEGUNDO_GRUPOS_DESPESA.txt"
    if t4.exists():
        campos = ["pessoal", "juros", "outras", "investimentos",
                  "inversoes", "amort", "reserva", "total"]
        linhas = []
        for registro in ler_tsv(t4):
            nome = _texto(registro.get("orgaos"))
            if not nome or nome.upper() == "TOTAL":
                continue
            valores = [_numero(registro.get(c)) or "0,00" for c in campos]
            linhas.append([nome] + valores)
        resultado["despesa_uo_grupo.csv"] = gravar(
            destino, "despesa_uo_grupo.csv",
            ["uo_nome", "pessoal", "juros", "outras_correntes", "investimentos",
             "inversoes", "amortizacao", "reserva", "total"], linhas)

    # T7: quadro geral da receita, com a árvore completa
    t7 = volume / "T7_QUADRO_GERAL_DA_RECEITA.txt"
    if t7.exists():
        linhas = []
        for registro in ler_tsv(t7):
            codigo = _texto(registro.get("cod_texto"))
            descricao = _texto(registro.get("descricao"))
            valor = (_numero(registro.get("valor_desdobramento"))
                     or _numero(registro.get("valor_especie"))
                     or _numero(registro.get("valor_categoria")))
            if not (codigo and descricao and valor):
                continue
            linhas.append([codigo, nivel_do_codigo(codigo), descricao,
                           _texto(registro.get("COD_FONTE")), valor])
        resultado["receita_geral.csv"] = gravar(
            destino, "receita_geral.csv",
            ["codigo", "nivel", "especificacao", "fonte", "valor"], linhas)

    # T5: pessoal consolidado por órgão
    t5 = volume / "T5_DEMONSTRATIVO_CONSOLIDADO_CATEGORIA_PESSOAL.txt"
    if t5.exists():
        linhas = []
        for registro in ler_tsv(t5):
            nome = _texto(registro.get("orgao"))
            if not nome or nome.upper() == "TOTAL":
                continue
            linhas.append([nome,
                           _numero(registro.get("ativo")) or "0,00",
                           _numero(registro.get("inativo")) or "0,00",
                           _numero(registro.get("terceirizado")) or "0,00",
                           _numero(registro.get("total")) or "0,00"])
        resultado["pessoal_consolidado.csv"] = gravar(
            destino, "pessoal_consolidado.csv",
            ["orgao_nome", "ativos", "inativos", "terceirizados", "total"], linhas)

    return resultado


# --------------------------------------------------------------------------
# Volume 2 — Anexo II
# --------------------------------------------------------------------------

def importar_anexo_ii(volume: Path, destino: Path) -> dict[str, int]:
    resultado = {}

    # tabela4: demonstrativo dos recursos financeiros (o de 622 páginas)
    pasta = volume / "tabela4"
    if pasta.exists():
        linhas = []
        for arquivo in sorted(pasta.glob("*.txt")):
            registros = preencher(ler_tsv(arquivo), ["nome_uo", "nome_orgao"])
            for registro in registros:
                codigo = _texto(registro.get("cod_texto"))
                descricao = _texto(registro.get("descricao"))
                valor = (_numero(registro.get("valor_desdobramento"))
                         or _numero(registro.get("valor_especie"))
                         or _numero(registro.get("valor_categoria")))
                if not (codigo and descricao and valor):
                    continue
                linhas.append([so_uo(registro.get("nome_orgao")),
                               so_uo(registro.get("nome_uo")),
                               codigo, nivel_do_codigo(codigo),
                               _texto(registro.get("COD_FONTE")),
                               descricao, valor])
        resultado["recursos_financeiros.csv"] = gravar(
            destino, "recursos_financeiros.csv",
            ["orgao_nome", "uo_nome", "codigo", "nivel", "fonte",
             "especificacao", "valor"], linhas)

    # tabela3: detalhamento da categoria de pessoal
    pasta = volume / "tabela3"
    if pasta.exists():
        linhas = []
        for arquivo in sorted(pasta.glob("*.txt")):
            registros = preencher(ler_tsv(arquivo),
                                  ["nome_uo", "nome_orgao", "classificacao"])
            for registro in registros:
                categoria = _texto(registro.get("categoria"))
                if not categoria:
                    continue
                linhas.append([so_uo(registro.get("nome_orgao")),
                               so_uo(registro.get("nome_uo")),
                               _texto(registro.get("classificacao")),
                               categoria,
                               _numero(registro.get("quantidade")) or "0,00",
                               _numero(registro.get("valor")) or ""])
        resultado["pessoal.csv"] = gravar(
            destino, "pessoal.csv",
            ["orgao_nome", "uo_nome", "classificacao", "categoria",
             "quantidade", "valor"], linhas)

    # tabela2: fonte de recurso e grupo de despesa.
    #
    # Cuidado com o layout: cada fonte ocupa VÁRIAS linhas, uma por IAG, e
    # o valor da fonte só aparece na linha de subtotal (a que traz "Total"
    # na coluna IAG). A linha onde o nome da fonte aparece contém apenas o
    # primeiro IAG — usá-la subestima a fonte. Na ALMG, por exemplo, a
    # fonte 10 vale R$ 2,04 bi no subtotal e R$ 1,60 bi na primeira linha.
    #
    # A última linha de cada unidade traz "TOTAL" na coluna da fonte: é a
    # soma da unidade, marcada aqui como papel "total" para não ser somada
    # junto com as parcelas.
    pasta = volume / "tabela2"
    if pasta.exists():
        campos = ("PESSOAL E ENCARGOS SOCIAIS", "OUTRAS DESPESAS CORRENTES",
                  "INVESTIMENTOS", "INVERSÕES FINANCEIRAS")
        linhas = []
        for arquivo in sorted(pasta.glob("*.txt")):
            registros = preencher(ler_tsv(arquivo), ["nome_uo", "nome_orgao"])
            fonte_atual = ""
            for registro in registros:
                fonte = _texto(registro.get("FONTE / GRUPO DE DESPESA"))
                iag = _texto(registro.get("IAG"))
                total = _numero(registro.get("Total"))

                if fonte and fonte.upper() != "TOTAL":
                    fonte_atual = fonte           # abre uma fonte; valor vem depois
                    continue

                eh_total_da_uo = fonte.upper() == "TOTAL"
                eh_subtotal = iag.upper() == "TOTAL"
                if not (eh_total_da_uo or eh_subtotal) or not total:
                    continue

                linhas.append([so_uo(registro.get("nome_orgao")),
                               so_uo(registro.get("nome_uo")),
                               "TOTAL DA UNIDADE" if eh_total_da_uo else fonte_atual,
                               "total" if eh_total_da_uo else "parcela"]
                              + [_numero(registro.get(c)) or "0,00" for c in campos]
                              + [total])
        resultado["fonte_grupo_despesa.csv"] = gravar(
            destino, "fonte_grupo_despesa.csv",
            ["orgao_nome", "uo_nome", "fonte", "papel", "pessoal",
             "outras_correntes", "investimentos", "inversoes", "total"], linhas)

    return resultado


# --------------------------------------------------------------------------
# Volume 3 — Anexo III
# --------------------------------------------------------------------------

def importar_anexo_iii(volume: Path, destino: Path) -> dict[str, int]:
    resultado = {}

    t1 = volume / "consolidado" / "T1_INVESTIMENTO_POR_EMPRESA.txt"
    if t1.exists():
        campos = ["tesouro_ordinario", "tesouro_vinculado", "outras_entidades",
                  "operacao_credito", "alienacao", "convenios",
                  "recursos_proprios", "outras_origens", "total"]
        linhas = []
        for registro in ler_tsv(t1):
            nome = _texto(registro.get("orgaos"))
            if not nome or nome.upper() == "TOTAL":
                continue
            linhas.append([nome] + [_numero(registro.get(c)) or "0,00" for c in campos])
        resultado["investimento_estatais.csv"] = gravar(
            destino, "investimento_estatais.csv", ["uo_nome"] + campos, linhas)

    pasta = volume / "tabela2"
    if pasta.exists():
        linhas = []
        for arquivo in sorted(pasta.glob("*.txt")):
            registros = preencher(ler_tsv(arquivo), ["orgao", "uo"])
            for registro in registros:
                especificacao = _texto(registro.get("especificacao"))
                valor = _numero(registro.get("valor")) or _numero(registro.get("total"))
                if not (especificacao and valor):
                    continue
                nivel = _texto(registro.get("nivel")) or "1"
                linhas.append([so_uo(registro.get("orgao")), so_uo(registro.get("uo")),
                               nivel if nivel.isdigit() else "1", especificacao, valor])
        resultado["investimento_detalhe.csv"] = gravar(
            destino, "investimento_detalhe.csv",
            ["orgao_nome", "uo_nome", "nivel", "especificacao", "valor"], linhas)

    return resultado


# --------------------------------------------------------------------------
# Volume 4 — Anexo IV
# --------------------------------------------------------------------------

def importar_anexo_iv(volume: Path, destino: Path) -> dict[str, int]:
    resultado = {}

    pasta = volume / "tabela1"
    if pasta.exists():
        linhas = []
        for arquivo in sorted(pasta.glob("*.txt")):
            for registro in preencher(ler_tsv(arquivo), ["orgao", "uo"]):
                territorio = _texto(registro.get("territorio"))
                valor = _numero(registro.get("valor"))
                if not (territorio and valor):
                    continue
                # cada arquivo traz uma linha TOTAL que repete a soma da UO
                if territorio.upper() == "TOTAL":
                    continue
                # 'ESTADUAL' não é uma região: são obras de alcance em todo o
                # estado. Fica como categoria própria, sem virar município.
                regiao = re.sub(r"^REGIÃO INTERMEDIÁRIA DE\s*", "", territorio, flags=re.I)
                linhas.append([so_uo(registro.get("orgao")), so_uo(registro.get("uo")),
                               titulo(regiao), valor])
        resultado["regionalizado.csv"] = gravar(
            destino, "regionalizado.csv",
            ["orgao_nome", "uo_nome", "regiao", "valor"], linhas)

    # tabela2: obra a obra, com o município onde será executada
    pasta = volume / "tabela2"
    if pasta.exists():
        linhas = []
        for arquivo in sorted(pasta.glob("*.txt")):
            registros = preencher(ler_tsv(arquivo),
                                  ["territorio", "municipio", "orgao", "nome_uo"])
            for registro in registros:
                obra = _texto(registro.get("obra"))
                municipio = _texto(registro.get("municipio"))
                if not obra or obra.upper() == "TOTAL" or not municipio:
                    continue
                tesouro = _numero(registro.get("tesouro")) or "0,00"
                outros = _numero(registro.get("outros")) or "0,00"
                total = _soma(tesouro, outros)
                if total == "0,00":
                    continue
                regiao = re.sub(r"^REGIÃO INTERMEDIÁRIA DE\s*", "",
                                _texto(registro.get("territorio")), flags=re.I)
                linhas.append([titulo(regiao), titulo(municipio),
                               so_uo(registro.get("orgao")), so_uo(registro.get("nome_uo")),
                               _texto(registro.get("nome_acao")),
                               re.sub(r"^\d+\s*-\s*", "", obra),
                               tesouro, outros, total])
        resultado["obras_municipio.csv"] = gravar(
            destino, "obras_municipio.csv",
            ["regiao", "municipio", "orgao_nome", "uo_nome", "acao",
             "obra", "tesouro", "outras_fontes", "total"], linhas)

    return resultado


def _soma(*valores: str) -> str:
    from decimal import Decimal
    total = Decimal(0)
    for valor in valores:
        limpo = (valor or "0").replace(".", "").replace(",", ".")
        try:
            total += Decimal(limpo)
        except Exception:
            pass
    return f"{total:.2f}".replace(".", ",")


# --------------------------------------------------------------------------
# orquestração
# --------------------------------------------------------------------------

# Cada volume é reconhecido por uma ASSINATURA — um arquivo ou pasta que
# só existe nele. Identificar por conteúdo, e não pelo nome da pasta, deixa
# o importador funcionar tanto no repositório oficial (volume1/data/…)
# quanto num zip baixado e renomeado (data-volume 1/…).
ASSINATURAS = {
    1: ("T4_DEMONSTRATIVO_DESPESA_POR_ORGAOS*", "T1_DEMONSTRATIVO_CONSOLIDADO*"),
    2: ("tabela4",),
    3: ("consolidado",),
    4: ("tabela2",),
    5: ("qdd*",),
    6: ("qdd*",),
    7: ("qdd*",),
}

# Nomes de pasta esperados, na ordem em que são tentados.
PADROES_NOME = (
    "volume{n}/data", "volume {n}/data", "volume_{n}/data",
    "data-volume {n}", "data-volume{n}", "data_volume_{n}",
    "volume{n}", "volume {n}", "volume_{n}",
)


def _tem_assinatura(pasta: Path, numero: int) -> bool:
    """A pasta contém o que caracteriza o volume `numero`?"""
    for padrao in ASSINATURAS.get(numero, ()):
        if any(pasta.glob(padrao)):
            # tabela2 existe nos volumes 2 e 4; o 2 também tem tabela4
            if numero == 4 and any(pasta.glob("tabela4")):
                return False
            return True
    return False


def _achar_volume(raiz: Path, numero: int) -> Path | None:
    """Localiza a pasta de dados do volume `numero` abaixo de `raiz`.

    Tenta primeiro os nomes conhecidos; se nenhum servir, varre as pastas
    procurando a assinatura de conteúdo. Assim uma renomeação no
    repositório de origem não quebra a importação.
    """
    for molde in PADROES_NOME:
        candidato = raiz / molde.format(n=numero)
        if candidato.is_dir() and _tem_assinatura(candidato, numero):
            return candidato

    # busca ampla, limitada a três níveis para não varrer o repositório todo
    for profundidade in ("*", "*/*", "*/*/*"):
        for candidato in sorted(raiz.glob(profundidade)):
            if not candidato.is_dir():
                continue
            if candidato.name in (".git", "pdf", "img", "logs", "capas", "wiki"):
                continue
            if _tem_assinatura(candidato, numero):
                return candidato
    return None


IMPORTADORES = {
    1: ("Anexo I — demonstrativos consolidados", importar_anexo_i),
    2: ("Anexo II — orçamento fiscal por unidade", importar_anexo_ii),
    3: ("Anexo III — investimento das estatais", importar_anexo_iii),
    4: ("Anexo IV — regionalizado e obras", importar_anexo_iv),
}


def inspecionar(origem: Path) -> list[tuple[int, str, str]]:
    """Diz onde cada volume foi encontrado, sem importar nada.

    Serve para conferir o caminho antes de configurar o GitHub Actions —
    e para descobrir o que mudou quando a importação parar de achar algo.
    """
    relatorio = []
    for numero, (titulo, _) in IMPORTADORES.items():
        volume = _achar_volume(origem, numero)
        if volume is None:
            relatorio.append((numero, titulo, ""))
            continue
        try:
            caminho = str(volume.relative_to(origem))
        except ValueError:
            caminho = str(volume)
        relatorio.append((numero, titulo, caminho))
    return relatorio


def importar(origem: Path, destino: Path) -> list[tuple[str, str, int]]:
    """Converte os volumes brutos para os CSV do projeto."""
    relatorio: list[tuple[str, str, int]] = []

    volumes = {}
    for numero, (titulo, funcao) in IMPORTADORES.items():
        volume = _achar_volume(origem, numero)
        volumes[numero] = volume
        if volume is None:
            relatorio.append((titulo, "volume não encontrado", 0))
            continue
        for arquivo, quantidade in funcao(volume, destino).items():
            relatorio.append((titulo, arquivo, quantidade))

    # Complementos: os demonstrativos novos usam os mesmos bancos de origem,
    # mas não faziam parte do importador histórico. Mantê-los aqui é importante
    # para que o workflow automático nunca deixe uma página nova com dados
    # antigos quando o repositório volumes-loa for atualizado.
    try:
        from .importar_complementares import importar_complementares
        extras = importar_complementares(volumes.get(1), volumes.get(2), volumes.get(3), destino)
        for arquivo, quantidade in extras.items():
            relatorio.append(("Demonstrativos complementares", arquivo, quantidade))
    except Exception as exc:
        relatorio.append(("Demonstrativos complementares", f"ERRO: {exc}", 0))

    return relatorio
