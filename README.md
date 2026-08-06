# Site do Orçamento de Minas Gerais

Transforma os anexos da Lei Orçamentária Anual — hoje **1.793 páginas em
5 PDFs** — em um site navegável, sem retirar um único dado.

100% Python, com Poetry e MkDocs Material. Um comando gera tudo.

---

## Índice

1. [Começando](#1-começando)
2. [Importando os dados oficiais](#2-importando-os-dados-oficiais)
3. [Como o projeto está organizado](#3-como-o-projeto-está-organizado)
4. [Os comandos](#4-os-comandos)
5. [Publicando um demonstrativo novo](#5-publicando-um-demonstrativo-novo)
6. [Referência da configuração](#6-referência-da-configuração)
7. [As validações](#7-as-validações)
8. [Publicando no GitHub Pages](#8-publicando-no-github-pages)
9. [Atualização automática dos dados](#9-atualização-automática-dos-dados)
10. [Perguntas frequentes](#10-perguntas-frequentes)

---

## 1. Começando

O projeto usa **Poetry**. Se você ainda não o tem:

```bash
pipx install poetry        # ou: pip install --user poetry
```

Depois, dentro da pasta do projeto:

```bash
# uma vez só, na primeira vez
poetry install

# a partir daqui, no dia a dia
poetry run loa serve
```

Abra <http://127.0.0.1:8000>. Salvou um arquivo? A página recarrega sozinha.

O Poetry cria e gerencia o ambiente virtual sozinho — você não precisa
ativar nada. Se preferir não digitar `poetry run` toda vez:

```bash
poetry env activate        # imprime o comando de ativação; rode-o
loa serve                  # agora funciona direto
```

O arquivo `poetry.lock` fixa a versão exata de cada dependência. Ele é
versionado junto com o código de propósito: garante que a sua máquina, a
do colega e o servidor de publicação instalem exatamente as mesmas
bibliotecas. Nunca edite esse arquivo à mão — para atualizar uma
dependência, rode `poetry update`.

---

## 2. Importando os dados oficiais

Os dados vêm dos **sete volumes** do datapackage — os mesmos arquivos que
geram os PDFs. Baixe-os e rode:

```bash
poetry run loa importar ~/Downloads/arquivos_data
```

O comando encontra as pastas `data-volume 1` a `data-volume 7` em qualquer
nível abaixo do caminho informado, converte tudo para o padrão da casa
(CSV com `;`, decimal `,`, centavos) e grava em `dados/`.

| Volume | Vira |
| --- | --- |
| 1 | Demonstrativos consolidados do Anexo I |
| 2 | Recursos financeiros, pessoal e fontes por unidade orçamentária |
| 3 | Investimento das empresas controladas |
| 4 | Regionalizado e obras por município |
| 5–7 | Quadro de detalhamento da despesa *(ainda não publicado — veja abaixo)* |

Depois:

```bash
poetry run loa check     # confere se as somas fecham
poetry run loa serve     # vê o resultado
```

**Nada é digitado à mão.** Se um número mudar na origem, ele muda no site
e em nenhum outro lugar.

### O que ainda não está publicado

Os volumes 5, 6 e 7 trazem o **Quadro de Detalhamento da Despesa** — a
despesa aberta por ação orçamentária, elemento e fonte. É a base mais
detalhada do orçamento inteiro e cabe naturalmente no projeto, mas ainda
não tem um bloco em `config/demonstrativos.yml`. Para publicá-la, escreva
um importador análogo aos existentes em `loa/importar.py` e um bloco de
configuração — o padrão está todo pronto.

## 3. Como o projeto está organizado

```
loa-mg/
├── config/                  ← VOCÊ MEXE AQUI
│   ├── demonstrativos.yml       o que aparece no site
│   ├── glossario.yml            termos técnicos e suas explicações
│   └── site.yml                 nome do site, cores, menu
│
├── dados/                   ← GERADO por `loa importar`
│   └── *.csv                    convertidos dos sete volumes
│
├── paginas/                 ← VOCÊ ESCREVE AQUI
│   ├── index.md                 página inicial
│   ├── como-ler.md              introdução ao orçamento
│   └── sobre.md                 sobre o projeto
│
├── loa/                     ← o programa (raramente precisa mexer)
│   ├── importar.py              lê os volumes brutos e grava os CSV
│   ├── build.py                 monta as páginas
│   ├── dados.py                 lê os CSV
│   ├── formato.py               R$ 1.234.567,89
│   ├── glossario.py             tooltips automáticos
│   ├── validacao.py             confere se as somas fecham
│   ├── cli.py                   os comandos loa build/serve/check/new
│   └── componentes/
│       ├── cards.py             os quadrinhos de resumo
│       ├── tabela.py            a tabela filtrável e expansível
│       ├── grafico.py           gráficos em SVG
│       └── mapa.py              mapa das regiões de Minas
│
├── tema/                    ← aparência (mexe pouco)
│   ├── loa.css
│   └── loa.js                   único arquivo JavaScript do projeto
│
├── docs/                    ← GERADO. não edite, não versione
├── site/                    ← GERADO. o site pronto
└── mkdocs.yml               ← GERADO a partir de config/site.yml
```

**A regra de ouro:** tudo que você precisa mudar no dia a dia está em
`config/`, `dados/` e `paginas/`. As três primeiras pastas. O resto é
maquinário.

---

## 4. Os comandos

| Comando | O que faz |
| --- | --- |
| `poetry run loa importar <pasta>` | Converte os sete volumes do datapackage em CSV. |
| `poetry run loa procedencia` | Mostra de onde vieram os dados publicados. |
| `poetry run loa serve` | Gera o site e abre no navegador, recarregando sozinho. É o comando do dia a dia. |
| `poetry run loa build` | Gera o site final na pasta `site/`. |
| `poetry run loa check` | Só roda as conferências de consistência, sem gerar nada. Rápido. |
| `poetry run loa new arquivo.csv` | Lê o CSV e imprime um bloco de configuração pronto para colar. |

E os comandos do próprio Poetry que você vai usar:

| Comando | O que faz |
| --- | --- |
| `poetry install` | Instala tudo que o projeto precisa, na versão travada pelo `poetry.lock`. |
| `poetry add <pacote>` | Acrescenta uma dependência e atualiza o lock. |
| `poetry update` | Atualiza as dependências dentro dos limites do `pyproject.toml`. |
| `poetry check` | Confere se o `pyproject.toml` está válido. |

Os nomes estão em inglês de propósito: são os mesmos do MkDocs
(`mkdocs build`, `mkdocs serve`). Quem já conhece um, conhece o outro.

Use `poetry run loa build --estrito` quando quiser que o comando **falhe** se alguma
soma não fechar. É o que o GitHub Actions faz antes de publicar.

---

## 5. Publicando um demonstrativo novo

Sem escrever uma linha de Python. Quatro passos.

### Passo 1 — coloque o CSV em `dados/`

Padrão da casa: separador `;`, decimal `,`, codificação UTF-8. Arquivos
`.csv.gz` também funcionam.

### Passo 2 — peça o rascunho da configuração

```bash
poetry run loa new despesa_por_funcao.csv
```

Ele lê as colunas do arquivo e imprime um bloco quase pronto.

### Passo 3 — cole em `config/demonstrativos.yml`

Cole dentro do anexo certo, ajuste os títulos e escreva o `resumo` e a
`explicacao` — essas duas frases são o que faz o cidadão entender a
tabela. Vale o tempo gasto nelas.

### Passo 4 — veja

```bash
poetry run loa serve
```

Pronto. A página, o menu, o filtro, a exportação e a busca já existem.

---

## 6. Referência da configuração

Tudo abaixo vai dentro de um bloco de demonstrativo em
`config/demonstrativos.yml`.

### Campos de texto

| Campo | Para que serve |
| --- | --- |
| `id` | Vira o endereço da página. Só letras minúsculas e hífen. |
| `titulo` | Título da página e do menu. |
| `base_legal` | O artigo de lei que exige o demonstrativo. |
| `resumo` | **Uma frase**, em português de gente, sobre o que a tabela mostra. Aparece em destaque no topo. |
| `explicacao` | Texto mais longo, dentro de uma caixa que abre ao clique. É onde você ensina a ler. |

### Dados

| Campo | Para que serve |
| --- | --- |
| `dados` | Nome do arquivo em `dados/`. |
| `filtro` | Usa só parte do arquivo. Ex.: `{lado: receita}`. |
| `ordenar_por` | Ordena pela coluna indicada, do maior para o menor. |

### Colunas

```yaml
colunas:
  - {campo: uo_nome, titulo: "Unidade Orçamentária", tipo: texto}
  - {campo: total,   titulo: "Total",                tipo: dinheiro}
```

`tipo` pode ser `texto`, `dinheiro`, `quantidade` ou `percentual`.
Dinheiro sai sempre com `R$` e centavos, alinhado à direita.

### Hierarquia

Quando os dados têm uma coluna de nível (1, 2, 3…), a tabela vira uma
árvore que abre e fecha:

```yaml
hierarquia: {campo_nivel: nivel}
nivel_aberto: 2        # níveis acima de 2 começam recolhidos
```

A hierarquia sai **dos próprios dados**. Não existe tabela auxiliar em
lugar nenhum do projeto.

### Uma página por grupo

É isto que transforma 622 páginas de PDF em navegação de verdade:

```yaml
agrupar_por: uo_nome        # uma página por unidade orçamentária
prefixo_slug: "regiao-"     # opcional, entra no endereço
filtro_resumo: {especificacao: "TOTAL"}   # evita contar duas vezes na visão geral
colunas_resumo:             # colunas da página de visão geral
  - {campo: uo_nome, titulo: "Unidade", tipo: texto}
  - {campo: valor,   titulo: "Valor",   tipo: dinheiro}
```

Gera uma **visão geral** consolidada mais uma página completa por grupo,
todas no menu.

### Cards

```yaml
cards:
  - {titulo: "Despesa total", campo: total, funcao: soma}
  - {titulo: "Unidades",      funcao: contagem}
  - {titulo: "ICMS", campo: total, funcao: valor_de,
     filtro: {especificacao: "ICMS"}, nota: "principal tributo"}
```

Funções: `soma`, `contagem`, `maximo`, `valor_de`.

### Gráficos

```yaml
graficos:
  - tipo: barras            # ou: rosca
    titulo: "As 12 maiores dotações"
    rotulo: uo_nome
    valor: total
    limite: 12              # o resto vira "Demais"
    filtro: {nivel: "2"}    # opcional
```

Os gráficos são desenhados em SVG pelo Python. Não há biblioteca de
gráficos em JavaScript no projeto — o site carrega rápido, imprime bem e
funciona sem internet.

### Mapa

```yaml
mapa:
  titulo: "Investimento por região"
  regiao: regiao            # coluna com o nome da região
  valor: valor
```

Por padrão desenha um **mapa de blocos**: cada região é um quadrado
posicionado mais ou menos onde ela fica no estado. Para exibir o mapa
geográfico de verdade, baixe as regiões intermediárias no site do IBGE,
converta para GeoJSON e salve em `dados/regioes-mg.geojson` — o programa
detecta sozinho.

---

## 7. As validações

Ninguém confere à mão se 1.793 páginas fecham. O programa confere.

```yaml
validacoes:
  - {tipo: soma_igual, campo: total, esperado: "146969637358,00",
     descricao: "soma das unidades = total da despesa fiscal"}

  - {tipo: colunas_somam, total: total,
     parcelas: [pessoal, juros, outras_correntes, investimentos]}

  - {tipo: niveis_fecham, campo_nivel: nivel, campo: total}

  - {tipo: sem_vazios, campos: [uo_nome, total]}
```

| Tipo | Confere |
| --- | --- |
| `soma_igual` | A soma de uma coluna bate com um valor conhecido. |
| `colunas_somam` | Em cada linha, as parcelas somam o total. |
| `niveis_fecham` | Cada linha-pai é igual à soma dos seus filhos. |
| `sem_vazios` | Não há célula obrigatória em branco. |

Rode `poetry run loa check` a qualquer momento. No GitHub Actions isso roda antes de
publicar: **se não fechar, o site não vai ao ar**.

Este é o argumento mais forte do projeto na hora de apresentar. O PDF
apenas *presume* que os números fecham; aqui a máquina *garante*.

---

## 8. Publicando no GitHub Pages

O arquivo `.github/workflows/publicar.yml` já está pronto. No repositório:

1. **Settings → Pages → Source: GitHub Actions**.
2. Faça push para a branch `main`.

A publicação dispara sozinha sempre que mudar algo em `dados/`, `config/`,
`paginas/`, `loa/` ou `tema/`. Como o servidor de dados envia as
atualizações direto para o repositório, o site se atualiza sem ninguém
precisar rodar nada.

---

## 9. Atualização automática dos dados

Os dados da LOA mudam ao longo da tramitação. O painel busca a versão nova
sozinho, reimporta, confere se as somas fecham e republica — sem ninguém
rodar nada.

### O que acontece a cada atualização

```
repositório de dados muda
        ↓
painel baixa os dados oficiais
        ↓
poetry run loa importar        →  converte os volumes em CSV
        ↓
poetry run loa procedencia     →  registra origem, commit e data
        ↓
poetry run loa check           →  AS SOMAS FECHAM?
        ↓                              ↓ não
     sim                          para aqui; o site continua
        ↓                          exibindo a versão anterior
publica no GitHub Pages
```

O `loa check` no meio do caminho é o ponto importante: **se os números não
fecharem, nada vai ao ar**. É melhor um painel um dia atrasado que um
painel com números inconsistentes.

### Passo a passo

Onde estão os dados no repositório de origem: em `splor-mg/volumes-loa` os
volumes ficam em `volume1/data/`, `volume2/data/` … na raiz. Não existe uma
pasta `data/` única. O importador localiza cada volume **pelo conteúdo**,
não pelo nome da pasta, então uma renomeação futura não quebra nada.

---

**Passo 1 — Criar o token de leitura.**

Abra <https://github.com/settings/personal-access-tokens/new> e preencha:

| Campo | Valor |
| --- | --- |
| Token name | `painel-loa-leitura-dados` |
| Resource owner | **`splor-mg`** (não o seu usuário) |
| Expiration | 90 dias — anote a data |
| Repository access | Only select repositories → `splor-mg/volumes-loa` |
| Permissions → Repository permissions → Contents | **Read-only** |

Clique em *Generate token* e copie o valor. Ele aparece **uma vez só**.

Use um token *fine-grained*, não um clássico: o fine-grained dá leitura a um
repositório específico, o clássico daria acesso a tudo que você tem.

Sobre o *Resource owner*: como `volumes-loa` pertence à organização
`splor-mg`, o token precisa ser emitido no contexto dela. Se a organização
exigir aprovação de administrador, o token fica "pending" até alguém
aprovar — o botão de aprovação está em Settings da organização →
Personal access tokens.

---

**Passo 2 — Guardar o token no repositório do painel.**

No **seu** repositório do painel: Settings → Secrets and variables →
Actions → *New repository secret*.

- Name: `DADOS_TOKEN`
- Secret: cole o token

Depois de salvar, ninguém consegue ler o valor de volta — nem você. Se
perder, gere outro.

---

**Passo 3 — Ajustar as URLs do site.**

Em `config/site.yml`, troque `SEU-USUARIO/loa-mg` pelo seu repositório nas
três linhas indicadas. O `site_url` precisa bater com a URL do Pages e
terminar com barra, senão os links internos apontam para o lugar errado.

Em `.github/workflows/atualizar-dados.yml`, confira o topo:

```yaml
env:
  REPO_DADOS: splor-mg/volumes-loa
  PASTA_DADOS: "."      # a raiz do repositório de origem
```

O ponto está certo para a estrutura atual do `volumes-loa`.

---

**Passo 4 — Ligar o GitHub Pages.**

Settings → Pages → Source: **GitHub Actions**.

---

**Passo 5 — Rodar e ver.**

Actions → **Atualizar dados da LOA** → *Run workflow* → Run.

Acompanhe os passos. O que esperar de cada um:

| Passo | O que confirma |
| --- | --- |
| Baixar os dados oficiais | o token funciona e tem acesso |
| Localizar os volumes da LOA | achou `volume1/data`, `volume2/data`… |
| Importar os dados | converteu os volumes em CSV |
| Registrar a procedência | gravou origem, commit e data |
| Conferir a consistência | as somas do orçamento fecham |
| Verificar se algo mudou | há dado novo a publicar |
| Publicar no GitHub Pages | site no ar |

Ao final, abra a página **Dados abertos** do site: o bloco "Procedência
desta versão" mostra a data, o commit de origem e o que disparou a
atualização. O rodapé de cada demonstrativo traz a mesma informação.

**É esse bloco que prova a automação.** Faça uma alteração qualquer no
`volumes-loa` — inclusive num PDF, como sua equipe sugeriu — rode o
workflow e o commit exibido muda. É a demonstração que você queria, sem
apoiar o painel numa fonte frágil.

---

### Se algo der errado

| Sintoma no log | Causa provável | O que fazer |
| --- | --- | --- |
| `Repository not found` ou 404 no checkout | token sem acesso, expirado, ou pendente de aprovação da organização | conferir o *Resource owner* e a aprovação |
| `Volumes não encontrados: 1, 2, …` | `PASTA_DADOS` errado | o log lista as pastas disponíveis; ajuste o valor |
| Falha em "Conferir a consistência" | os dados de origem estão inconsistentes | é o sistema fazendo o trabalho dele; o site continua na versão anterior |
| `Permission denied` ao dar push | o workflow não pode escrever | Settings → Actions → General → Workflow permissions → *Read and write* |
| Site publica mas sem estilo | `site_url` diferente da URL real do Pages | corrigir em `config/site.yml` |

Para conferir os caminhos antes de subir qualquer coisa, rode na sua
máquina, com o `volumes-loa` clonado ao lado:

```bash
poetry run loa inspecionar ../volumes-loa
```

---

### Um alerta que não é técnico

O repositório do painel é **público** e o `volumes-loa` é **privado**. Ao
publicar, os CSVs importados passam a ficar visíveis para qualquer pessoa.

Para a LOA já enviada à Assembleia isso é justamente o objetivo — são dados
públicos, e o projeto existe para torná-los acessíveis. Mas vale confirmar
com a sua chefia antes de publicar num repositório pessoal, especialmente
se houver alguma remessa ainda não protocolada. É uma conversa de cinco
minutos que evita um problema grande.

Enquanto isso, para testar sem publicar nada: deixe o Pages desligado. O
workflow roda, importa, valida e mostra o resumo — só não publica.

---

### Quando roda sozinho

| Disparo | Quando | Para quê |
| --- | --- | --- |
| Manual | botão na aba Actions | testar, ou publicar na hora |
| Agendado | de hora em hora, 8h–20h, dias úteis | rede de segurança |
| Aviso da origem | segundos após o dado mudar | atualização imediata |

Os dois primeiros já funcionam. O terceiro é opcional e exige instalar um
arquivo no `volumes-loa` — está em
`exemplos/aviso-para-o-repo-de-dados.yml`. Recomendação: deixe para depois
que o fluxo estiver rodando. A diferença é esperar minutos em vez de
segundos, e mexer num repositório de produção para isso não vale o risco de
estreia.

Se nada mudou na origem, o workflow encerra sem publicar. Não gera commits
nem publicações vazias.

### Quando o token expira

O workflow falha no passo "Baixar os dados oficiais" com erro de
autenticação — não silenciosamente. Gere um novo e substitua o segredo.

Anote a validade no calendário da equipe: um token de 90 dias vence
justamente quando ninguém está olhando.

### Por que não buscar direto no site da ALMG

A página da lei no site da Assembleia parece a fonte mais natural, mas não
serve como fonte de dados:

- **Ela publica o texto da lei, não os anexos tabulares.** Os números que o
  painel exibe — demonstrativos por unidade orçamentária, por região, por
  município — não estão no HTML da página.
- **Não existe API.** Só há a página feita para leitura humana. Ler dados
  dela significa raspar HTML, que quebra a cada mudança de layout do site,
  sem aviso e sem controle nosso.
- **O acesso automatizado é bloqueado.** Uma requisição simples à página
  devolve HTTP 403.
- **A lei sancionada é publicada uma vez.** O que muda ao longo da
  tramitação são as remessas de dados — e essas nascem no datapackage, não
  no site.

O caminho correto é o inverso: o dado nasce no datapackage da SPLOR, gera o
PDF que vai à Assembleia *e* alimenta o painel. Uma fonte, dois destinos.

Se um dia for útil monitorar a página da ALMG, o lugar disso é um aviso
("a página da lei mudou, confira"), nunca uma fonte de números.

### Por que não usar a pasta de PDF como fonte

A sugestão de acompanhar `volumes-loa/pdf` é boa na intenção — é onde a
mudança fica visível — mas o painel não consegue se alimentar dali:

- **Extrair dados de PDF perde linhas.** Nós medimos: na primeira versão
  deste projeto, a extração dos PDF deixou 5 hierarquias sem fechar em
  1.226 linhas. Com os dados tabulares, as 16 validações fecham.
- **O PDF é o produto, não a fonte.** Ele é gerado *a partir* dos dados.
  Ler o PDF para reconstruir os dados é fotografar um documento para
  redigitá-lo.
- **Um PDF alterado nem sempre significa dado alterado.** Um ajuste de
  formatação mudaria o arquivo sem mudar um número.

A parte aproveitável da sugestão — **ver a automação funcionando ao mexer
no repositório de origem** — está atendida: o workflow observa o
repositório inteiro, e o bloco de procedência muda a cada execução. Você
consegue a demonstração sem apoiar o painel numa fonte frágil.

## 10. Perguntas frequentes

**Preciso saber programar para manter isso?**
Não. Para publicar demonstrativos, basta editar YAML e escrever texto. O
comando `loa new` gera o rascunho do YAML para você.

**E se eu quebrar alguma coisa?**
`poetry run loa check` avisa antes de publicar. E como `docs/`, `site/` e
`mkdocs.yml` são gerados, apagar qualquer um deles não perde nada: é só
rodar `poetry run loa build` de novo.

**Preciso versionar a pasta `dados/`?**
Não é obrigatório: ela é reproduzível a partir dos volumes com
`poetry run loa importar`. Versionar facilita a vida de quem só quer rodar
o site sem baixar o datapackage inteiro; o projeto vem com ela preenchida
por esse motivo.

**Por que `loa check` acusa falha na primeira execução?**
Porque ele está certo. Os dados de amostra foram extraídos dos PDFs, e a
extração de PDF perde linhas: em `recursos_financeiros.csv` restaram **5
hierarquias que não fecham, em 1.226 linhas** — cinco lugares onde um
valor-filho se perdeu no caminho.

Isso é uma demonstração do recurso, não um defeito do gerador. Rode:

```bash
poetry run loa check
```

e ele diz exatamente qual linha-pai não bate com a soma dos seus filhos, e
de quanto é a diferença. Ninguém encontraria esses cinco pontos folheando
622 páginas de PDF.

Quando você trocar a amostra pelos dados oficiais do datapackage, a
validação passa a fechar — e a partir daí qualquer nova divergência que
aparecer é sinal real de problema na origem.

Enquanto isso: `poetry run loa build` publica assim mesmo, avisando;
`poetry run loa build --estrito` se recusa a publicar. O GitHub Actions usa a versão estrita.

**E o PDF, acaba?**
Como documento de consulta, sim: o site passa a ser a referência, e cada
demonstrativo ganha link permanente. Se a Assembleia exigir o documento
formal para protocolo, o botão *Imprimir* de cada página gera a versão
impressa a partir do mesmo pipeline — o site vira a fonte, o PDF vira a
impressão.

**Por que quase nada de JavaScript?**
Porque a equipe é de Python. O único arquivo `.js` do projeto é genérico
(filtro, ordenação, expansão, exportação) e serve para todas as tabelas,
inclusive as que ainda serão criadas. Ninguém vai precisar editá-lo para
publicar conteúdo novo.

**Aguenta 600 unidades orçamentárias?**
Sim. O site é estático e a opção `navigation.prune` do MkDocs Material faz
o menu carregar só o ramo aberto. Cada página carrega apenas a sua tabela.
