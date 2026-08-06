"""Procedência dos dados.

Registra DE ONDE e DE QUANDO veio cada versão dos dados publicados, e
mostra isso no site. Três motivos:

1. **Transparência.** Quem consulta o orçamento precisa saber qual versão
   está vendo. A LOA muda entre o projeto de lei, o autógrafo e a lei
   sancionada; um número sem data é um número sem sentido.

2. **Auditabilidade.** Com o commit de origem registrado, qualquer pessoa
   pode conferir o dado exibido contra o arquivo que o gerou.

3. **Sinal visível de automação.** É o que permite ver o GitHub Actions
   funcionando: mude qualquer coisa no repositório de origem e o rodapé do
   site muda junto, com data, hora e commit novos.

O arquivo `dados/procedencia.json` é escrito pelo workflow, nunca à mão.
Se ele não existir, o site funciona igual — apenas sem o rastro.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Horário de Brasília, sem depender de tzdata no runner.
FUSO_BRASILIA = timezone(timedelta(hours=-3))

ARQUIVO = "procedencia.json"


@dataclass
class Procedencia:
    origem: str = ""          # ex.: splor-mg/volumes-loa
    commit: str = ""          # SHA do commit de origem
    commit_url: str = ""      # link para o commit
    mensagem: str = ""        # assunto do commit de origem
    atualizado_em: str = ""   # ISO 8601
    disparo: str = ""         # o que acionou a atualização

    @property
    def commit_curto(self) -> str:
        return self.commit[:7] if self.commit else ""

    @property
    def data_amigavel(self) -> str:
        """'2026-08-05T14:32:10-03:00' -> '5 de agosto de 2026, 14h32'."""
        if not self.atualizado_em:
            return ""
        try:
            quando = datetime.fromisoformat(self.atualizado_em)
        except ValueError:
            return self.atualizado_em

        if quando.tzinfo is None:
            quando = quando.replace(tzinfo=timezone.utc)
        quando = quando.astimezone(FUSO_BRASILIA)

        meses = ("janeiro", "fevereiro", "março", "abril", "maio", "junho",
                 "julho", "agosto", "setembro", "outubro", "novembro", "dezembro")
        return (f"{quando.day} de {meses[quando.month - 1]} de {quando.year}, "
                f"{quando.hour:02d}h{quando.minute:02d}")

    def existe(self) -> bool:
        return bool(self.atualizado_em or self.commit)

    # ---------------------------------------------------------------- textos

    def linha_curta(self) -> str:
        """Uma linha para o rodapé das páginas de demonstrativo."""
        if not self.existe():
            return ""
        partes = []
        if self.data_amigavel:
            partes.append(f"Dados atualizados em {self.data_amigavel}")
        if self.commit_curto:
            alvo = (f"[`{self.commit_curto}`]({self.commit_url})"
                    if self.commit_url else f"`{self.commit_curto}`")
            origem = f" a partir de `{self.origem}`" if self.origem else ""
            partes.append(f"versão{origem} {alvo}")
        return " — ".join(partes) + "."

    def bloco_markdown(self) -> str:
        """Bloco completo para a página de dados abertos."""
        if not self.existe():
            return (
                '!!! warning "Procedência não registrada"\n'
                "    Este site foi gerado a partir dos arquivos locais em `dados/`,\n"
                "    sem passar pela automação. Rode `poetry run loa importar` e\n"
                "    publique pelo GitHub Actions para que a origem seja registrada.\n"
            )

        # Uma linha de tabela por campo: no admonition do Material, linhas
        # de texto seguidas viram um parágrafo só e tudo se embola.
        itens = []
        if self.data_amigavel:
            itens.append(("Atualizado em", f"{self.data_amigavel} (horário de Brasília)"))
        if self.origem:
            itens.append(("Origem dos dados", f"`{self.origem}`"))
        if self.commit_curto:
            alvo = (f"[`{self.commit_curto}`]({self.commit_url})"
                    if self.commit_url else f"`{self.commit_curto}`")
            itens.append(("Versão de origem", alvo))
        if self.mensagem:
            itens.append(("Alteração", self.mensagem))
        if self.disparo:
            itens.append(("Atualização disparada por", self.disparo))

        linhas = ['!!! info "Procedência desta versão"', ""]
        linhas.append("    | | |")
        linhas.append("    | --- | --- |")
        for rotulo, valor in itens:
            linhas.append(f"    | **{rotulo}** | {valor} |")
        linhas.append("")
        return "\n".join(linhas)


def ler(pasta_dados: Path) -> Procedencia:
    """Lê dados/procedencia.json. Ausência não é erro."""
    arquivo = pasta_dados / ARQUIVO
    if not arquivo.exists():
        return Procedencia()
    try:
        bruto = json.loads(arquivo.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return Procedencia()

    campos = {c: bruto.get(c, "") for c in Procedencia.__dataclass_fields__}
    return Procedencia(**campos)


def escrever(pasta_dados: Path, **campos) -> Procedencia:
    """Grava a procedência. Usado pelo workflow, não pela equipe."""
    agora = datetime.now(FUSO_BRASILIA).isoformat(timespec="seconds")
    dados = {"atualizado_em": agora, **{k: v for k, v in campos.items() if v}}
    pasta_dados.mkdir(parents=True, exist_ok=True)
    (pasta_dados / ARQUIVO).write_text(
        json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return ler(pasta_dados)
