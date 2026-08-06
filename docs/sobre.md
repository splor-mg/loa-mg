# Sobre o projeto

## O que é

Este site é a Lei Orçamentária Anual do Estado de Minas Gerais publicada
como **documento navegável** em vez de arquivo para impressão.

Ele é gerado automaticamente a partir das mesmas bases de dados que
produzem o PDF oficial enviado à Assembleia Legislativa. Não há
digitação manual, não há recorte e cola, não há número que exista aqui e
não exista na origem.

## O que mudou em relação ao PDF

| Antes | Agora |
| --- | --- |
| 5 arquivos, 1.793 páginas | Um site, 409 páginas navegáveis |
| Citação por número de página | Link permanente para cada quadro |
| Busca só dentro de cada arquivo | Busca em todo o orçamento |
| Tabela como única forma de ver | Resumo, gráfico e mapa antes da tabela |
| Copiar número a número | Download em CSV em qualquer tabela |
| Somas conferidas a olho | Somas conferidas automaticamente a cada publicação |
| Difícil de ler no celular | Feito para o celular |

## Como é feito

* **Python** para ler os dados, calcular, validar e gerar as páginas.
* **Poetry** para fixar as versões das bibliotecas.
* **MkDocs Material** para o site estático.
* **GitHub Actions** para publicar sozinho quando os dados mudam.

Os dados vêm dos sete volumes do datapackage que a SPLOR já usa para
gerar os PDFs. Um comando (`poetry run loa importar`) os converte; nada é
digitado à mão.

Os gráficos e o mapa são desenhados em SVG pelo próprio Python — o site
não depende de nenhuma biblioteca de gráficos em JavaScript. O único
arquivo JavaScript do projeto cuida do filtro, da ordenação e da
exportação das tabelas, e é genérico: serve para todas.

Para publicar um demonstrativo novo não é preciso programar. Basta
descrever a tabela em um arquivo de configuração e rodar um comando.

## Transparência e limites

* Este site apresenta o **projeto de lei**. Os valores podem mudar durante
  a tramitação na Assembleia.
* O orçamento é uma **autorização de gasto**, não um registro do que foi
  gasto. Para acompanhar a execução, consulte o Portal da Transparência do
  Estado.
* Encontrou uma divergência entre este site e o documento oficial? Isso é
  um erro e queremos saber: abra uma questão no repositório do projeto.

## Créditos

Superintendência Central de Planejamento e Orçamento — Subsecretaria de
Planejamento e Orçamento — Secretaria de Estado de Planejamento e Gestão de
Minas Gerais.
