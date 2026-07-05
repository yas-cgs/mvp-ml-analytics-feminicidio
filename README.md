# MVP Machine Learning & Analytics - Feminicídio e tempo até decisão

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/yas-cgs/mvp-ml-analytics-feminicidio/blob/main/notebooks/MVP_ML_Analytics_Feminicidio.ipynb)

Projeto individual de pós-graduação para desenvolver um MVP de Machine Learning & Analytics com dados públicos do DataJud/CNJ sobre processos relacionados a feminicídio.

## Objetivo

Construir um problema de classificação binária para prever se um processo relacionado a feminicídio, em primeiro grau, terá uma decisão judicial substantiva em até 730 dias após o ajuizamento.

A variável-alvo é:

- `1`: houve decisão judicial substantiva em até 730 dias;
- `0`: não houve decisão substantiva dentro de 730 dias, considerando processos com tempo suficiente de acompanhamento ou decisão posterior ao prazo.

Processos sem decisão e com menos de 730 dias de acompanhamento são tratados como censurados e excluídos da modelagem principal.

## Fonte dos dados

O projeto parte de duas fontes de dados:

- `portal_cnj.csv`: arquivo separado por tabulações exportado do Portal CNJ. Ele contém uma linha por caso, com campos como tribunal, município, unidade judicial, número do processo no padrão da Resolução CNJ nº 65/2008, descrição da decisão e status de confidencialidade. Somente casos não confidenciais foram considerados.
- API Pública do DataJud/CNJ: API de dados judiciais do CNJ, consultada no projeto original por meio de `datajud_requester.py`. Ela fornece metadados detalhados do processo e histórico de movimentação para cada caso.

Nesta pasta do MVP, os dados usados na preparação estão em:

- `Data/processos.parquet`: metadados processuais;
- `Data/movimentos.parquet`: movimentos processuais relacionados por `numeroProcesso`.

A API Pública do DataJud não disponibiliza processos sigilosos. Como processos relacionados a feminicídio e violência doméstica podem tramitar sob sigilo, a base representa somente os processos públicos disponíveis e não necessariamente a totalidade dos casos existentes.

## Notebook principal

O relatório técnico executável está em:

- [`notebooks/MVP_ML_Analytics_Feminicidio.ipynb`](notebooks/MVP_ML_Analytics_Feminicidio.ipynb)

No Colab, o notebook carrega a base pública compactada por URL:

```text
https://raw.githubusercontent.com/yas-cgs/mvp-ml-analytics-feminicidio/main/data/mvp/base_modelagem.csv.gz
```

## Estrutura do repositório

```text
.
├── data/
│   ├── feminicidio/
│   │   ├── processos.parquet
│   │   └── movimentos.parquet
│   └── mvp/
│       ├── base_modelagem.csv.gz
│       └── base_modelagem_metadata.json
├── notebooks/
│   └── MVP_ML_Analytics_Feminicidio.ipynb
├── resultados/
│   └── ...
├── scripts/
│   └── analise_exploratoria.py
├── src/
│   └── preparar_base_mvp.py
├── requirements.txt
└── README.md
```

## Como executar

### No Google Colab

1. Abra o notebook pelo badge "Open in Colab".
2. Execute as células em ordem.
3. O notebook baixará a base `data/mvp/base_modelagem.csv.gz` diretamente do GitHub com `requests` e `raise_for_status()`.

### Localmente

Instale as dependências:

```bash
python -m pip install -r requirements.txt
```

Recrie a base de modelagem a partir dos Parquets originais:

```bash
python src/preparar_base_mvp.py
```

Execute o notebook:

```bash
jupyter nbconvert --to notebook --execute notebooks/MVP_ML_Analytics_Feminicidio.ipynb --output MVP_ML_Analytics_Feminicidio.executado.ipynb
```

Depois do primeiro `push`, valide se a URL Raw da base pública abre sem autenticação.

## Dicionário resumido da base de modelagem

| Variável | Descrição |
|---|---|
| `tribunal` | Tribunal de origem do registro público. |
| `classe_codigo` | Código da classe processual. |
| `sistema_nome` | Sistema processual informado no registro. |
| `formato_nome` | Formato do processo. |
| `ano_ajuizamento` | Ano do ajuizamento. |
| `mes_ajuizamento` | Mês do ajuizamento. |
| `orgao_julgador_municipio_ibge` | Código IBGE do município do órgão julgador, quando disponível. |
| `quantidade_assuntos` | Quantidade de assuntos associados ao processo. |
| `assunto_homicidio_qualificado` | Indicador de assunto Homicídio Qualificado. |
| `assunto_violencia_domestica_mulher` | Indicador de assuntos de violência doméstica ou contra a mulher. |
| `assunto_crime_tentado` | Indicador de assunto Crime Tentado. |
| `assunto_ameaca` | Indicador de assunto Ameaça. |
| `assunto_homicidio_simples` | Indicador de assunto Homicídio Simples. |
| `assunto_arma` | Indicador agregado de assuntos relacionados a armas. |
| `assunto_medida_protetiva` | Indicador agregado de medida protetiva. |
| `decisao_substantiva_ate_730d` | Alvo binário do MVP. |

## Limitações

- A base pública do DataJud não inclui processos sigilosos.
- A variável-alvo depende dos movimentos registrados e dos códigos de decisão disponíveis.
- Processos recentes sem decisão suficiente foram excluídos por censura.
- O modelo identifica associações, não causalidade.
- Os resultados não devem ser usados para decisões individuais sobre processos, pessoas, vítimas, réus, magistrados ou unidades judiciais.
- Diferenças por tribunal podem refletir tanto fenômenos reais quanto qualidade, disponibilidade e padrões de registro dos dados.

## Observação metodológica

O notebook não utiliza como preditores número de processo, `id`, nomes pessoais, nomes de magistrados, datas de decisão, duração até decisão, movimentos posteriores, `dataHoraUltimaAtualizacao`, `@timestamp` ou variáveis derivadas diretamente do resultado.
