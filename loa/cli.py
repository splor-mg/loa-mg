"""Linha de comando.

    loa build              gera o site em docs/ e o mkdocs.yml
    loa serve              gera e abre no navegador com recarga automática
    loa check              só roda as validações de consistência
    loa new <arquivo.csv>  cria um bloco de config pronto para colar

Os nomes dos comandos seguem o padrão do MkDocs, em inglês, de propósito:
quem já usa `mkdocs build` não precisa aprender nada novo.
"""

import argparse
import subprocess
import sys
from pathlib import Path

from .build import gerar
from .dados import ler
from .importar import importar


def _raiz() -> Path:
    """Sobe diretórios até achar a pasta config/."""
    atual = Path.cwd().resolve()
    for pasta in [atual, *atual.parents]:
        if (pasta / "config" / "demonstrativos.yml").exists():
            return pasta
    print("ERRO: não achei config/demonstrativos.yml. Rode o comando dentro do projeto.")
    sys.exit(1)


def _relatar(resultados) -> int:
    if not resultados:
        print("\nNenhuma validação configurada.")
        return 0

    falhas = [r for r in resultados if not r.ok]
    print(f"\nValidações de consistência ({len(resultados)} regras):\n")
    for resultado in resultados:
        print(resultado)

    if falhas:
        print(f"\n{len(falhas)} validação(ões) falharam. "
              "Os dados de origem estão inconsistentes — confira antes de publicar.")
        return 1

    print("\nTudo fecha.")
    return 0


def comando_build(args) -> int:
    raiz = _raiz()
    resultados = gerar(raiz)
    codigo = _relatar(resultados)

    if codigo and args.estrito:
        print("\nBuild interrompido (--estrito).")
        return codigo

    subprocess.run(["mkdocs", "build", "--clean"], cwd=raiz, check=True)
    print(f"\nSite gerado em {raiz / 'site'}")
    return 0


def comando_serve(args) -> int:
    raiz = _raiz()
    _relatar(gerar(raiz))
    subprocess.run(["mkdocs", "serve", "--livereload"], cwd=raiz, check=False)
    return 0


def comando_check(args) -> int:
    return _relatar(gerar(_raiz()))


def comando_importar(args) -> int:
    """Converte os volumes brutos do datapackage nos CSV do projeto."""
    raiz = _raiz()
    origem = Path(args.origem).expanduser().resolve()
    if not origem.exists():
        print(f"ERRO: pasta não encontrada: {origem}")
        return 1

    print(f"Lendo de {origem}\n")
    relatorio = importar(origem, raiz / "dados")

    largura = max((len(a) for _, a, _ in relatorio), default=10)
    titulo_atual = None
    for titulo, arquivo, quantidade in relatorio:
        if titulo != titulo_atual:
            print(f"\n{titulo}")
            titulo_atual = titulo
        if quantidade:
            print(f"  {arquivo:<{largura}}  {quantidade:>8,} linhas".replace(",", "."))
        else:
            print(f"  {arquivo}")

    total = sum(q for _, _, q in relatorio)
    print(f"\n{total:,} linhas gravadas em dados/.".replace(",", "."))
    print("Agora rode: poetry run loa check")
    return 0


def comando_new(args) -> int:
    """Imprime um bloco de config já preenchido com as colunas do CSV."""
    raiz = _raiz()
    linhas = ler(raiz / "dados", args.arquivo)
    if not linhas:
        print("Arquivo vazio.")
        return 1

    colunas = list(linhas[0].keys())
    identificador = Path(args.arquivo).stem.replace("_", "-")

    print(f"""
# Cole este bloco em config/demonstrativos.yml, dentro do anexo desejado,
# e ajuste títulos e tipos de coluna.

      - id: {identificador}
        titulo: "TÍTULO DO DEMONSTRATIVO"
        base_legal: "Art. X da Lei Y"
        resumo: "Uma frase em português claro sobre o que esta tabela mostra."
        explicacao: |
          Explique aqui, para quem não é da área, como ler a tabela.
        dados: {args.arquivo}
        colunas:""")
    for coluna in colunas:
        tipo = "dinheiro" if any(p in coluna for p in ("valor", "total", "despesa", "receita")) else "texto"
        print(f'          - {{campo: {coluna}, titulo: "{coluna.replace("_", " ").title()}", tipo: {tipo}}}')
    print("""        cards:
          - {titulo: "Total", campo: valor, funcao: soma}
        validacoes:
          - {tipo: sem_vazios, campos: [%s]}
""" % colunas[0])
    return 0


def principal(argv=None) -> int:
    analisador = argparse.ArgumentParser(prog="loa", description="Gerador do site da LOA-MG")
    sub = analisador.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("build", help="gera o site")
    p.add_argument("--estrito", action="store_true", help="falha se alguma validação não passar")
    p.set_defaults(funcao=comando_build)

    p = sub.add_parser("serve", help="gera e serve com recarga automática")
    p.set_defaults(funcao=comando_serve)

    p = sub.add_parser("check", help="roda apenas as validações")
    p.set_defaults(funcao=comando_check)

    p = sub.add_parser("importar", help="converte os volumes brutos do datapackage")
    p.add_argument("origem", help="pasta com as pastas 'data-volume N'")
    p.set_defaults(funcao=comando_importar)

    p = sub.add_parser("new", help="cria um bloco de config a partir de um CSV")
    p.add_argument("arquivo")
    p.set_defaults(funcao=comando_new)

    args = analisador.parse_args(argv)
    return args.funcao(args)


if __name__ == "__main__":
    sys.exit(principal())
