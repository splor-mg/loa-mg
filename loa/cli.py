"""Linha de comando.

    loa build              gera o site em docs/ e o mkdocs.yml
    loa serve              gera e abre no navegador com recarga automática
    loa check              só roda as validações de consistência
    loa new <arquivo.csv>  cria um bloco de config pronto para colar
"""

import argparse
import subprocess
import sys
from pathlib import Path

from .build import gerar
from .dados import ler
from .importar import importar, inspecionar
from . import procedencia as proc


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


def comando_inspecionar(args) -> int:
    """Mostra onde cada volume foi encontrado, sem importar nada."""
    origem = Path(args.origem).expanduser().resolve()
    if not origem.exists():
        print(f"ERRO: pasta não encontrada: {origem}")
        return 1

    print(f"Procurando os volumes da LOA em {origem}\n")
    relatorio = inspecionar(origem)

    faltando = []
    for numero, titulo, caminho in relatorio:
        if caminho:
            print(f"  Volume {numero}  {titulo}")
            print(f"            encontrado em: {caminho}")
        else:
            print(f"  Volume {numero}  {titulo}")
            print(f"            NÃO ENCONTRADO")
            faltando.append(numero)

    if faltando:
        print(f"\nVolumes não encontrados: {', '.join(map(str, faltando))}.")
        print("Confira se o caminho informado é a raiz do repositório de dados.")
        print("Pastas no primeiro nível do caminho informado:")
        for item in sorted(p for p in origem.iterdir() if p.is_dir())[:20]:
            print(f"  {item.name}/")
        return 1

    print("\nTodos os volumes localizados. Pode rodar `loa importar`.")
    return 0


def comando_procedencia(args) -> int:
    """Registra de onde vieram os dados desta publicação.

    Chamado pelo GitHub Actions depois de `loa importar`. Sem argumentos,
    apenas mostra a procedência registrada.
    """
    raiz = _raiz()

    if not any([args.origem, args.commit, args.mensagem, args.disparo]):
        atual = proc.ler(raiz / "dados")
        if not atual.existe():
            print("Nenhuma procedência registrada.")
            print("Ela é gravada pelo GitHub Actions a cada atualização.")
            return 0
        print(f"Origem     : {atual.origem or '(não informada)'}")
        print(f"Commit     : {atual.commit or '(não informado)'}")
        print(f"Atualizado : {atual.data_amigavel}")
        if atual.mensagem:
            print(f"Alteração  : {atual.mensagem}")
        if atual.disparo:
            print(f"Disparo    : {atual.disparo}")
        return 0

    url = args.commit_url
    if not url and args.origem and args.commit:
        url = f"https://github.com/{args.origem}/commit/{args.commit}"

    registrada = proc.escrever(
        raiz / "dados",
        origem=args.origem,
        commit=args.commit,
        commit_url=url,
        mensagem=args.mensagem,
        disparo=args.disparo,
    )
    print("Procedência registrada:", registrada.linha_curta())
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

    p = sub.add_parser("inspecionar",
                       help="mostra onde cada volume foi encontrado, sem importar")
    p.add_argument("origem", help="raiz do repositório de dados")
    p.set_defaults(funcao=comando_inspecionar)

    p = sub.add_parser("procedencia",
                       help="registra ou mostra a origem dos dados publicados")
    p.add_argument("--origem", default="", help="repositório de origem (owner/repo)")
    p.add_argument("--commit", default="", help="SHA do commit de origem")
    p.add_argument("--commit-url", default="", help="link do commit (opcional)")
    p.add_argument("--mensagem", default="", help="assunto do commit de origem")
    p.add_argument("--disparo", default="", help="o que acionou a atualização")
    p.set_defaults(funcao=comando_procedencia)

    p = sub.add_parser("new", help="cria um bloco de config a partir de um CSV")
    p.add_argument("arquivo")
    p.set_defaults(funcao=comando_new)

    args = analisador.parse_args(argv)
    return args.funcao(args)


if __name__ == "__main__":
    sys.exit(principal())
