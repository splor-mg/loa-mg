# LOA-MG

Site dos demonstrativos da Lei Orçamentária Anual (LOA) de Minas Gerais.

O projeto transforma os dados produzidos no repositório `splor-mg/volumes-loa` em dados estruturados e publica o site no GitHub Pages.

## 1. Como os projetos se relacionam

```text
splor-mg/volumes-loa
        │
        │ dados oficiais
        ▼
     loa-mg
        │
        ├── importar → converte os dados em CSV
        ├── check    → verifica se os valores fecham
        └── build    → gera o site
```

O `volumes-loa` é a origem dos dados. O `loa-mg` é responsável por importar, validar e publicar esses dados.

No `volumes-loa`, os dados estão organizados nos sete volumes:

```text
volumes-loa/
├── volume1/data/
├── volume2/data/
├── volume3/data/
├── volume4/data/
├── volume5/data/
├── volume6/data/
└── volume7/data/
```

O importador do `loa-mg` identifica os volumes automaticamente pelo conteúdo. Não é necessário informar manualmente cada uma das sete pastas.

## 2. CLI do projeto

Depois de instalar o projeto com Poetry:

```bash
poetry run loa <comando>
```

### `inspecionar`

Localiza os volumes disponíveis sem importar os dados.

```bash
poetry run loa inspecionar ../volumes-loa
```

Serve para verificar se o projeto consegue encontrar corretamente os dados de origem.

### `importar`

Lê os dados do `volumes-loa` e gera os CSV utilizados pelo `loa-mg`.

```bash
poetry run loa importar ../volumes-loa
```

Os dados importados ficam em `dados/`.

### `check`

Executa as validações de consistência dos dados.

```bash
poetry run loa check
```

Verifica, entre outras coisas, se as somas dos demonstrativos fecham.

Se houver erro, a publicação deve ser interrompida.

Resultado esperado:

```text
[OK] Demonstrativo Consolidado do Orçamento Fiscal
[OK] Quadro Geral da Receita
[OK] Demonstrativo dos Recursos Financeiros
...
Tudo fecha.
```

### `procedencia`

Registra de onde vieram os dados importados.

Exemplo:

```bash
poetry run loa procedencia \
  --origem splor-mg/volumes-loa \
  --commit <commit> \
  --mensagem "<mensagem do commit>" \
  --disparo "execução manual"
```

Permite manter a rastreabilidade entre os dados publicados e a versão utilizada no `volumes-loa`.

### `build`

Gera o site a partir dos dados e das configurações.

```bash
poetry run loa build --estrito
```

O site gerado fica em `site/`.

## 3. Fluxo local

Para testar uma atualização manualmente:

```bash
cd ~/code/splor/loa-mg

poetry run loa inspecionar ../volumes-loa
poetry run loa importar ../volumes-loa
poetry run loa check
poetry run loa build --estrito
```

A ordem é:

```text
inspecionar
     ↓
 importar
     ↓
   check
     ↓
   build
```

Primeiro localizamos os dados, depois importamos, validamos e somente então geramos o site.

## 4. Atualização automática

O workflow `.github/workflows/atualizar-dados.yml` automatiza esse processo.

Ele:

1. baixa o `loa-mg`;
2. baixa o repositório privado `splor-mg/volumes-loa`;
3. identifica a versão/commit da origem;
4. instala o projeto;
5. localiza os volumes;
6. importa os dados;
7. registra a procedência;
8. executa `loa check`;
9. verifica se os dados realmente mudaram;
10. grava os novos CSV no `loa-mg`;
11. gera o site;
12. publica no GitHub Pages.

O workflow utiliza o segredo `DADOS_TOKEN` para acessar o repositório privado `volumes-loa`.

### Regra de segurança

A validação acontece antes da publicação:

```text
volumes-loa
     ↓
 importar
     ↓
   check
     │
     ├── erro → para o processo
     │
     └── OK
          ↓
        build
          ↓
     GitHub Pages
```

Assim, uma atualização com dados inconsistentes não deve substituir a versão válida que já está publicada.

## 5. Tags e versões

Atualmente, o repositório `volumes-loa` ainda não possui tags definidas.

A estrutura do `loa-mg` já está preparada para trabalhar com uma referência de versão da origem.

No workflow existe o input:

```yaml
referencia:
  description: "Branch ou tag do repositório de dados"
  default: main
```

Hoje, por padrão, a origem utilizada é `main`.

Quando a equipe definir o padrão de nomes das tags, será possível informar a tag nesse campo sem precisar alterar a estrutura principal do projeto.

Exemplo futuro:

```text
volumes-loa
   │
   ├── tag da versão definida pela equipe
   │
   ▼
GitHub Actions
   │
   ▼
loa-mg
   │
   ├── importar
   ├── check
   └── build
   │
   ▼
GitHub Pages
```

O nome e o padrão definitivo das tags devem ser definidos pela equipe antes de serem adotados no processo oficial.

## 6. Workflows

### `atualizar-dados.yml`

Responsável por buscar os dados do `volumes-loa`, importar, validar e publicar quando houver alteração.

Pode ser executado:

- manualmente pela aba **Actions**;
- de forma agendada;
- por `repository_dispatch`, quando o repositório de origem avisar que houve atualização.

### `publicar.yml`

Publica o site quando arquivos relevantes do `loa-mg` são alterados.

Fluxo:

```text
check
  ↓
build
  ↓
GitHub Pages
```

## 7. Estrutura simplificada

```text
loa-mg/
├── .github/
│   └── workflows/
│       ├── atualizar-dados.yml
│       └── publicar.yml
├── config/
│   └── demonstrativos.yml
├── dados/
│   └── *.csv
├── loa/
│   ├── cli.py
│   ├── importar.py
│   └── ...
├── paginas/
├── tema/
├── pyproject.toml
└── README.md
```

## 8. Resumo

```text
                REPOSITÓRIO DE ORIGEM
              splor-mg/volumes-loa
                       │
                       │ branch ou tag
                       ▼
                 GitHub Actions
                       │
                       ▼
                  loa importar
                       │
                       ▼
                   dados/*.csv
                       │
                       ▼
                    loa check
                       │
                ┌──────┴──────┐
                │             │
              erro             OK
                │             │
                ▼             ▼
              para         loa build
                              │
                              ▼
                       GitHub Pages
```

### Em uma frase

**`volumes-loa` fornece os dados; `loa-mg` importa, valida, organiza e publica os demonstrativos da LOA.**
