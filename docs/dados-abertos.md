# Dados abertos

!!! warning "Procedência não registrada"
    Este site foi gerado a partir dos arquivos locais em `dados/`,
    sem passar pela automação. Rode `poetry run loa importar` e
    publique pelo GitHub Actions para que a origem seja registrada.


Todo número exibido neste site vem dos arquivos abaixo — são os mesmos que geram o PDF oficial enviado à Assembleia Legislativa. Estão em CSV (separador `;`, decimal `,`, codificação UTF-8), abrem no Excel, no LibreOffice, no Python e no R.

| Arquivo | Linhas | Colunas | Download |
| --- | ---: | --- | --- |
| `categorias_economicas.csv` | 8 | `lado`, `nivel`, `especificacao`, `valor` | [baixar](arquivos/categorias_economicas.csv) |
| `consolidado_fiscal.csv` | 112 | `lado`, `nivel`, `especificacao`, `ordinaria`, `vinculada`, `total` | [baixar](arquivos/consolidado_fiscal.csv) |
| `despesa_uo_grupo.csv` | 101 | `uo_nome`, `pessoal`, `juros`, `outras_correntes`, `investimentos`, `inversoes`, `amortizacao`, `reserva`, `total` | [baixar](arquivos/despesa_uo_grupo.csv) |
| `fonte_grupo_despesa.csv` | 499 | `orgao_nome`, `uo_nome`, `fonte`, `pessoal`, `outras_correntes`, `investimentos`, `inversoes`, `total` | [baixar](arquivos/fonte_grupo_despesa.csv) |
| `investimento_detalhe.csv` | 61 | `orgao_nome`, `uo_nome`, `nivel`, `especificacao`, `valor` | [baixar](arquivos/investimento_detalhe.csv) |
| `investimento_estatais.csv` | 15 | `uo_nome`, `tesouro_ordinario`, `tesouro_vinculado`, `outras_entidades`, `operacao_credito`, `alienacao`, `convenios`, `recursos_proprios`, `outras_origens`, `total` | [baixar](arquivos/investimento_estatais.csv) |
| `obras_municipio.csv` | 261 | `regiao`, `municipio`, `orgao_nome`, `uo_nome`, `acao`, `obra`, `tesouro`, `outras_fontes`, `total` | [baixar](arquivos/obras_municipio.csv) |
| `pessoal.csv` | 287 | `orgao_nome`, `uo_nome`, `classificacao`, `categoria`, `quantidade`, `valor` | [baixar](arquivos/pessoal.csv) |
| `pessoal_consolidado.csv` | 62 | `orgao_nome`, `ativos`, `inativos`, `terceirizados`, `total` | [baixar](arquivos/pessoal_consolidado.csv) |
| `receita_geral.csv` | 1348 | `codigo`, `nivel`, `especificacao`, `fonte`, `valor` | [baixar](arquivos/receita_geral.csv) |
| `recursos_financeiros.csv` | 3421 | `orgao_nome`, `uo_nome`, `codigo`, `nivel`, `fonte`, `especificacao`, `valor` | [baixar](arquivos/recursos_financeiros.csv) |
| `regionalizado.csv` | 93 | `orgao_nome`, `uo_nome`, `regiao`, `valor` | [baixar](arquivos/regionalizado.csv) |

## Reprodutibilidade

O site inteiro é gerado por um comando:

```bash
loa build
```

Se um arquivo de dados mudar, o site muda junto — não existe número digitado à mão em nenhuma página.
