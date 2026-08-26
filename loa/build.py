"""Geração do site.

Lê os arquivos de `config/`, os dados de `dados/`, e escreve as páginas
markdown em `docs/` mais o `mkdocs.yml` com a navegação completa.

Ninguém precisa mexer neste arquivo para publicar um demonstrativo novo:
basta acrescentar um bloco em `config/demonstrativos.yml`.
"""

import re
import shutil
import unicodedata
from pathlib import Path

import yaml

from . import procedencia as proc
from . import validacao
from .componentes import cards, grafico, mapa, tabela
from .dados import filtrar, ler, valores_distintos
from .glossario import Glossario

# --------------------------------------------------------------------------
# utilidades
# --------------------------------------------------------------------------

def slug(texto: str) -> str:
    """'SECRETARIA DE ESTADO DE SAÚDE - SES' -> 'secretaria-de-estado-de-saude-ses'"""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", str(texto)) if unicodedata.category(c) != "Mn"
    )
    limpo = re.sub(r"[^a-zA-Z0-9]+", "-", sem_acento).strip("-").lower()
    return limpo[:70] or "sem-nome"


MINUSCULAS = {"de", "do", "da", "dos", "das", "e", "em", "a", "o", "no", "na", "para", "por", "com", "ao"}


def titulo_amigavel(texto: str) -> str:
    """'SECRETARIA DE ESTADO DE SAÚDE - SES' -> 'Secretaria de Estado de Saúde - SES'

    Preserva siglas (palavras curtas em maiúsculas e o trecho após o hífen).
    """
    partes = str(texto).split(" - ")
    nome = partes[0]
    sigla = " - ".join(partes[1:])

    palavras = []
    for i, palavra in enumerate(nome.split()):
        minuscula = palavra.lower()
        if i > 0 and minuscula in MINUSCULAS:
            palavras.append(minuscula)
        elif len(palavra) <= 4 and palavra.isupper() and not palavra.isalpha():
            palavras.append(palavra)
        else:
            palavras.append(palavra.capitalize())

    amigavel = " ".join(palavras)
    return f"{amigavel} - {sigla}" if sigla else amigavel


def ler_yaml(caminho: Path) -> dict:
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo de configuração não encontrado: {caminho}")
    return yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}


# --------------------------------------------------------------------------
# gerador
# --------------------------------------------------------------------------

class Gerador:
    def __init__(self, raiz: Path):
        self.raiz = raiz
        self.pasta_config = raiz / "config"
        self.pasta_dados = raiz / "dados"
        self.pasta_paginas = raiz / "paginas"
        self.pasta_docs = raiz / "docs"

        self.site = ler_yaml(self.pasta_config / "site.yml")
        self.estrutura = ler_yaml(self.pasta_config / "demonstrativos.yml")
        self.glossario = Glossario(ler_yaml(self.pasta_config / "glossario.yml"))

        # De onde vieram os dados desta publicação (ver loa/procedencia.py).
        self.procedencia = proc.ler(self.pasta_dados)

        self.nav: list = []
        self.resultados: list[validacao.Resultado] = []

    # ---------------------------------------------------------------- páginas

    def _cabecalho_pagina(self, dem: dict, sufixo: str = "") -> str:
        titulo = dem["titulo"] + (f" — {titulo_amigavel(sufixo)}" if sufixo else "")

        # `hide: toc` esconde a barra lateral direita (o índice da página).
        # Numa página de demonstrativo ela lista um item só — o título — e
        # em troca consome cerca de 240 px de largura, justamente onde a
        # tabela precisa deles. Escondê-la é o que mais alarga a tabela.
        partes = ["---", "hide:", "  - toc", "---", "", f"# {titulo}", ""]

        if dem.get("resumo"):
            partes += ["!!! abstract \"Em uma frase\"", f"    {dem['resumo']}", ""]
        if dem.get("base_legal"):
            partes += [f"**Base legal:** {dem['base_legal']}", ""]
        if dem.get("explicacao"):
            partes += ['!!! abstract "Como ler este demonstrativo"', ""]
            partes += ["    " + l for l in dem["explicacao"].strip().split("\n")]
            partes += [""]
        return "\n".join(partes)

    def _rodape_pagina(self, dem: dict, profundidade: int = 2) -> str:
        arquivo = dem["dados"]
        subir = "../" * profundidade
        return "\n".join([
            "",
            "---",
            "",
            '!!! info "Sobre estes dados"',
            f"    Fonte primária: `{arquivo}` — o mesmo arquivo que gera o PDF oficial.",
            f"    Baixe a base completa em [Dados abertos]({subir}dados-abertos.md).",
            "    Nenhuma linha foi omitida ou agregada nesta página.",
        ] + ([f"    {self.procedencia.linha_curta()}"]
             if self.procedencia.existe() else []) + [
            "",
        ])

    def _corpo(self, dem: dict, linhas: list[dict], identificador: str) -> str:
        blocos = []

        if dem.get("cards"):
            blocos.append(cards.montar(linhas, dem["cards"], dem.get("colunas")))

        if dem.get("mapa"):
            blocos.append(mapa.montar(linhas, dem["mapa"], self.pasta_dados))

        for config_grafico in dem.get("graficos", []):
            blocos.append(grafico.montar(linhas, config_grafico))

        blocos.append(
            tabela.montar(
                linhas=linhas,
                colunas=dem["colunas"],
                glossario=self.glossario,
                identificador=identificador,
                hierarquia=dem.get("hierarquia"),
                ordenar_por=dem.get("ordenar_por"),
                mostrar_total=dem.get("mostrar_total", True),
                nivel_aberto=dem.get("nivel_aberto", 2),
            )
        )
        return "\n\n".join(b for b in blocos if b)

    # ------------------------------------------------------------ demonstrativo

    def _gerar_demonstrativo(self, anexo: dict, dem: dict) -> tuple[str, object]:
        linhas = ler(self.pasta_dados, dem["dados"])
        linhas = filtrar(linhas, dem.get("filtro", {}))

        self.resultados += validacao.verificar(
            dem["titulo"], linhas, dem.get("validacoes", [])
        )

        base = self.pasta_docs / slug(anexo["id"]) / slug(dem["id"])
        base.mkdir(parents=True, exist_ok=True)

        agrupar = dem.get("agrupar_por") or []
        if isinstance(agrupar, str):
            agrupar = [agrupar]

        # ---- página principal do demonstrativo
        conteudo = [self._cabecalho_pagina(dem)]

        if agrupar:
            # A visão geral consolida os grupos. `filtro_resumo` evita contar
            # duas vezes quando os dados têm hierarquia (ex.: usar só a linha
            # TOTAL de cada unidade orçamentária).
            base_resumo = filtrar(linhas, dem.get("filtro_resumo", {}))
            colunas_resumo = dem.get("colunas_resumo") or [
                c for c in dem["colunas"] if c["campo"] != (dem.get("hierarquia") or {}).get("campo_nivel")
            ]
            dem_resumo = {
                **dem,
                "colunas": colunas_resumo,
                "hierarquia": None,
                "ordenar_por": dem.get("ordenar_resumo") or dem.get("ordenar_por"),
            }
            conteudo.append(
                self._corpo(
                    dem_resumo,
                    self._resumir(base_resumo, dem_resumo, agrupar[-1]),
                    slug(dem["id"]) + "-resumo",
                )
            )
            conteudo.append(
                "\n!!! tip \"Detalhamento completo\"\n"
                f"    Cada {agrupar[-1].replace('_', ' ')} tem página própria no menu "
                "à esquerda, com a tabela integral — exatamente como no PDF.\n"
            )
        else:
            conteudo.append(self._corpo(dem, linhas, slug(dem["id"])))

        conteudo.append(self._rodape_pagina(dem, profundidade=2))
        (base / "index.md").write_text("\n".join(conteudo), encoding="utf-8")

        caminho_indice = f"{slug(anexo['id'])}/{slug(dem['id'])}/index.md"
        if not agrupar:
            return dem["titulo"], caminho_indice

        # ---- uma página por grupo
        prefixo = dem.get("prefixo_slug", "")
        campo = agrupar[-1]
        filhos = [{"Visão geral": caminho_indice}]

        for valor in sorted(valores_distintos(linhas, campo)):
            recorte = [l for l in linhas if l.get(campo) == valor]
            if not recorte:
                continue
            pasta = base / (prefixo + slug(valor))
            pasta.mkdir(parents=True, exist_ok=True)

            texto = [
                self._cabecalho_pagina(dem, sufixo=valor),
                self._corpo(dem, recorte, slug(dem["id"]) + "-" + slug(valor)),
                self._rodape_pagina(dem, profundidade=3),
            ]
            (pasta / "index.md").write_text("\n".join(texto), encoding="utf-8")
            filhos.append({titulo_amigavel(valor): f"{slug(anexo['id'])}/{slug(dem['id'])}/{prefixo}{slug(valor)}/index.md"})

        return dem["titulo"], filhos

    def _resumir(self, linhas: list[dict], dem: dict, campo_grupo: str) -> list[dict]:
        """Consolida os grupos numa tabela-resumo para a visão geral."""
        from .formato import para_decimal

        numericas = [c for c in dem["colunas"] if c.get("tipo") in ("dinheiro", "quantidade")]

        # Colunas de classificação que os cards podem filtrar (como `papel`)
        # são preservadas: sem elas, um card com `filtro: {papel: total}`
        # não encontraria nada na visão geral e exibiria zero.
        classificadoras = [c for c in ("papel", "lado", "nivel")
                           if linhas and c in linhas[0]]

        resumo: dict[str, dict] = {}
        for linha in linhas:
            chave = linha.get(campo_grupo, "")
            alvo = resumo.setdefault(
                chave,
                {campo_grupo: chave, **{c: linha.get(c, "") for c in classificadoras}},
            )
            for coluna in numericas:
                campo = coluna["campo"]
                alvo[campo] = para_decimal(alvo.get(campo, 0)) + para_decimal(linha.get(campo))
        return list(resumo.values())

    # -------------------------------------------------------------- páginas fixas

    def _copiar_tema(self) -> None:
        destino = self.pasta_docs / "assets"
        destino.mkdir(parents=True, exist_ok=True)
        for arquivo in (self.raiz / "tema").glob("*"):
            if arquivo.is_file():
                shutil.copy(arquivo, destino / arquivo.name)

    def _copiar_paginas_fixas(self) -> None:
        for arquivo in sorted(self.pasta_paginas.glob("*.md")):
            destino = self.pasta_docs / arquivo.name
            destino.write_text(arquivo.read_text(encoding="utf-8"), encoding="utf-8")

    def _gerar_glossario(self) -> None:
        texto = (
            "# Glossário do orçamento\n\n"
            "Estes termos aparecem sublinhados ao longo do site — passe o mouse "
            "(ou toque, no celular) para ver a explicação sem sair da tabela.\n\n"
            + self.glossario.como_markdown()
            + "\n"
        )
        (self.pasta_docs / "glossario.md").write_text(texto, encoding="utf-8")

    def _gerar_dados_abertos(self) -> None:
        destino = self.pasta_docs / "arquivos"
        destino.mkdir(parents=True, exist_ok=True)

        linhas = [
            "# Dados abertos",
            "",
            self.procedencia.bloco_markdown(),
            "",
            "| Arquivo | Linhas | Colunas | Download |",
            "| --- | ---: | --- | --- |",
        ]
        for arquivo in sorted(self.pasta_dados.glob("*.csv")):
            if arquivo.name == proc.ARQUIVO:
                continue
            shutil.copy(arquivo, destino / arquivo.name)
            registros = ler(self.pasta_dados, arquivo.name)
            colunas = ", ".join(f"`{c}`" for c in (registros[0].keys() if registros else []))
            linhas.append(
                f"| `{arquivo.name}` | {len(registros)} | {colunas} | "
                f"[baixar](arquivos/{arquivo.name}) |"
            )

        linhas += [
            "",

            "",
        ]
        (self.pasta_docs / "dados-abertos.md").write_text("\n".join(linhas), encoding="utf-8")

    # -------------------------------------------------------------------- mkdocs

    def _escrever_mkdocs(self) -> None:
        config = dict(self.site.get("mkdocs", {}))
        config["nav"] = self.nav

        cabecalho = (
            "# ARQUIVO GERADO AUTOMATICAMENTE POR `loa build`.\n"
            "# Não edite aqui: mexa em config/site.yml e config/demonstrativos.yml.\n"
        )
        corpo = yaml.safe_dump(config, allow_unicode=True, sort_keys=False)

        # O MkDocs precisa de tags !!python/name: para os ícones do Material.
        # O yaml.safe_dump não as escreve, então usamos o marcador PY! no
        # config/site.yml e o traduzimos aqui.
        corpo = re.sub(r"['\"]?PY!([\w\.]+)['\"]?", r"!!python/name:\1", corpo)

        (self.raiz / "mkdocs.yml").write_text(cabecalho + corpo, encoding="utf-8")

    # ---------------------------------------------------------------------- run

    def executar(self) -> list[validacao.Resultado]:
        if self.pasta_docs.exists():
            shutil.rmtree(self.pasta_docs)
        self.pasta_docs.mkdir(parents=True)

        self._copiar_tema()
        self._copiar_paginas_fixas()

        self.nav = [{"Início": [{"Início": "index.md"}]}]

        for anexo in self.estrutura.get("anexos", []):
            pasta = self.pasta_docs / slug(anexo["id"])
            pasta.mkdir(parents=True, exist_ok=True)

            abertura = [f"# {anexo['titulo']}", ""]
            if anexo.get("descricao"):
                abertura += [anexo["descricao"], ""]
            abertura += ["## Demonstrativos deste anexo", ""]
            for dem in anexo.get("demonstrativos", []):
                abertura.append(f"- [{dem['titulo']}]({slug(dem['id'])}/index.md) — {dem.get('resumo', '')}")
            abertura.append("")
            (pasta / "index.md").write_text("\n".join(abertura), encoding="utf-8")

            filhos = [{"Sobre o anexo": f"{slug(anexo['id'])}/index.md"}]
            for dem in anexo.get("demonstrativos", []):
                titulo, destino = self._gerar_demonstrativo(anexo, dem)
                filhos.append({titulo: destino})

            self.nav[0]["Início"].append({anexo["titulo"]: filhos})

        self._gerar_glossario()
        self._gerar_dados_abertos()

        extras = [{"Como ler o orçamento": "como-ler.md"},
                  {"Glossário": "glossario.md"},
                  {"Dados abertos": "dados-abertos.md"},
                  {"Sobre a LOA": "sobre.md"}]
        self.nav += [e for e in extras if (self.pasta_docs / list(e.values())[0]).exists()]

        self._escrever_mkdocs()
        return self.resultados


def gerar(raiz: Path) -> list[validacao.Resultado]:
    return Gerador(raiz).executar()
