---
name: integrar-bases
description: Executa o Integration Pipeline completo entre duas tabelas CSV — do perfil ao relatório final — com um único comando. Orquestra as skills analisar-tabela, comparar-colunas, identificar-chave e gerar-relatorio em sequência, passando o output de cada etapa como input da próxima via arquivo. Valida o Domain Context no início e reporta cobertura de colunas. Use SEMPRE que o usuário quiser integrar duas bases do início ao fim sem executar cada skill manualmente. Disparar quando o usuário disser "integra essas duas bases", "quero o pipeline completo", "cruza essas tabelas e gera o relatório", ou simplesmente fornecer dois arquivos CSV querendo o resultado final.
input:
  - type: csv
    path: "{table_a}"
    description: Primeira tabela (obrigatório)
  - type: csv
    path: "{table_b}"
    description: Segunda tabela (obrigatório)
  - type: json
    path: "output/contexts/context_{domain}.json"
    description: Domain Context (opcional — usa defaults orçamentários se ausente)
    optional: true
output:
  - type: json
    path: output/analisar_tabela_{table_a}.json
  - type: json
    path: output/analisar_tabela_{table_b}.json
  - type: json
    path: output/comparar_colunas_{table_a}__{table_b}.json
  - type: json
    path: output/identificar_chave_{table_a}__{table_b}.json
  - type: html
    path: output/reports/relatorio_{table_a}__{table_b}_{date}.html
---

## Contexto do projeto

```
PROJECT_ROOT = /home/luiza-maluf/Área de trabalho/tcc/fase01
```

Esta skill é a orquestradora do pipeline. Ela **não executa análises** — delega cada etapa para a skill especializada correspondente e gerencia os paths entre etapas.

---

## Entrada esperada

```
<arquivo_a.csv>  <arquivo_b.csv>  [--context output/contexts/context_dominio.json]
```

Exemplos:
```
data/raw/empenhos.csv  data/raw/pagamentos.csv
data/raw/escolas.csv  data/raw/matriculas.csv  --context output/contexts/context_educacao.json
```

Se o usuário não informar `--context`, use o contexto default (domínio orçamentário federal).

---

## Pipeline de execução

Execute as etapas na ordem abaixo. A cada etapa:
1. Informe qual etapa está iniciando
2. Execute a lógica da skill correspondente
3. Verifique que o arquivo de saída foi criado
4. Prossiga para a próxima etapa

### Etapa 0 — Validar Domain Context

```python
import sys
sys.path.insert(0, PROJECT_ROOT)

from src.config.context_loader import load_context
from src.agent.context_validator import validate_context
import pandas as pd

# Carregar metadados mínimos das tabelas para validação
df_a_cols = list(pd.read_csv(table_a, sep=";", encoding="utf-8", nrows=0, dtype=str).columns)
df_b_cols = list(pd.read_csv(table_b, sep=";", encoding="utf-8", nrows=0, dtype=str).columns)

context = load_context(context_path)  # None se não fornecido
result = validate_context(context, df_a_cols, df_b_cols)
```

Exibir:
```
[0/5] VALIDAÇÃO DE CONTEXTO
  Domínio  : {result.domain_name} {"(padrão)" if result.is_default else ""}
  Cobertura: {result.coverage:.0%} ({len(result.recognized_columns)}/{result.total_columns} colunas)
```

Se `result.warning` existir, exibir o aviso e perguntar ao usuário se deseja continuar ou executar `/definir-contexto` primeiro. Se o usuário continuar, prosseguir normalmente.

### Etapa 1 — Analisar tabelas

Execute a lógica da skill `analisar-tabela` para cada tabela individualmente.

Paths de saída:
- `output/analisar_tabela_{stem_a}.json`
- `output/analisar_tabela_{stem_b}.json`

onde `stem_a` = nome do arquivo sem extensão (ex: `data/raw/empenhos.csv` → `empenhos`).

Exibir ao iniciar:
```
[1/5] ANALISANDO TABELAS
  → {table_a}
  → {table_b}
```

### Etapa 2 — Comparar colunas (modo automático)

Execute a lógica da skill `comparar-colunas` no **modo automático**:
- Leia os dois JSONs gerados na Etapa 1
- Selecione automaticamente os pares candidatos (não peça ao usuário)
- Passe o Domain Context carregado na Etapa 0 para enriquecer a seleção

Path de saída: `output/comparar_colunas_{stem_a}__{stem_b}.json`

Exibir ao iniciar:
```
[2/5] COMPARANDO COLUNAS (automático)
  Selecionando pares candidatos a partir dos perfis...
```

### Etapa 3 — Identificar chave

Execute a lógica da skill `identificar-chave` como **Decision Layer**:
- Leia o JSON da Etapa 2 como Evidence Layer (não regenere candidatos)
- Use LLM para raciocinar sobre a melhor Integration Key

Path de saída: `output/identificar_chave_{stem_a}__{stem_b}.json`

Exibir ao iniciar:
```
[3/5] IDENTIFICANDO CHAVE DE INTEGRAÇÃO
  Analisando {N} candidatos com LLM...
```

### Etapa 4 — Gerar relatório

Execute a lógica da skill `gerar-relatorio`:
- Leia o JSON da Etapa 3
- Gere o relatório Markdown completo

Path de saída: `output/reports/relatorio_{stem_a}__{stem_b}_{YYYY-MM-DD}.md`

Exibir ao iniciar:
```
[4/5] GERANDO RELATÓRIO
```

### Conclusão

```
══════════════════════════════════════════════════════════════════════
PIPELINE CONCLUÍDO
  Integration Key: {col_a} ↔ {col_b}
  Confiança      : {confidence}
  Relatório      : output/reports/relatorio_{stem_a}__{stem_b}_{date}.md

Arquivos intermediários:
  output/analisar_tabela_{stem_a}.json
  output/analisar_tabela_{stem_b}.json
  output/comparar_colunas_{stem_a}__{stem_b}.json
  output/identificar_chave_{stem_a}__{stem_b}.json
══════════════════════════════════════════════════════════════════════
```

---

## Tratamento de erros

- Se uma etapa falhar, informe claramente qual etapa falhou e o motivo.
- Não apague arquivos de etapas anteriores — o usuário pode retomar a partir do ponto de falha.
- Se o arquivo de saída de uma etapa já existir (execução anterior), pergunte ao usuário se deseja reutilizar (`usar cache`) ou reprocessar.

---

## Cuidados

- Use `stem` (nome sem extensão e sem diretório) nos nomes dos arquivos de saída, não o path completo.
- Normalize o stem: lowercase, substitua espaços e caracteres especiais por `_`.
- O Domain Context é injetado em todas as etapas que o suportam — não repita o `load_context` mais de uma vez.
