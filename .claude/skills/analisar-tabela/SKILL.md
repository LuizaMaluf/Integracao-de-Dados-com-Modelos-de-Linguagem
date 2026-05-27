---
name: analisar-tabela
description: Analisa estruturalmente e semanticamente uma tabela CSV. Perfila cada coluna (dtype, cardinalidade, nulos, unicidade, top-5 valores, comprimento médio), detecta grupos de domínio (usando Domain Context se disponível, ou defaults orçamentários), identifica padrões conhecidos e sugere candidatas a chave primária. Use SEMPRE que o usuário quiser explorar uma tabela CSV nova, entender a estrutura de uma base, identificar colunas-chave, ou preparar dados para integração com outra tabela. Também disparar quando o usuário disser "o que tem nessa tabela", "me mostra as colunas", "quais são as chaves", "analisa esse CSV", ou simplesmente soltar um caminho de arquivo CSV no chat.
input:
  - type: csv
    path: "{table}"
    description: Tabela a ser analisada (obrigatório)
  - type: json
    path: "output/contexts/context_{domain}.json"
    description: Domain Context (opcional — usa defaults orçamentários se ausente)
    optional: true
output:
  - type: json
    path: output/analisar_tabela_{table_stem}.json
---

## Contexto do projeto

```
PROJECT_ROOT = /home/luiza-maluf/Área de trabalho/tcc/fase01
```

Módulos disponíveis (use quando o projeto estiver instalado):
- `src.analyzers.structural` — `profile_column`, `cardinality_label`
- `src.analyzers.semantic` — `find_domain_group`, `semantic_score`
- `src.transformers.pattern_detector` — `detect_pattern`
- `src.config.context_loader` — `load_context` ← use este para obter grupos e padrões

Para usar os módulos:
```python
import sys
sys.path.insert(0, "/home/luiza-maluf/Área de trabalho/tcc/fase01")
```

Se a importação falhar, execute a lógica inline conforme as seções abaixo.

JSON de saída: `output/analisar_tabela_{stem}.json`

---

## Carregamento do Domain Context

Antes de detectar grupos de domínio, carregue o contexto ativo:

```python
from src.config.context_loader import load_context

# context_path: fornecido via --context, ou None para usar defaults
context = load_context(context_path)
DOMAIN_GROUPS = context.semantic_groups
PATTERNS = context.key_patterns
```

Se os módulos não estiverem disponíveis, use os grupos hardcoded da seção 3 como fallback.

---

## O que fazer

O usuário vai fornecer o caminho de um arquivo CSV (em `$ARGUMENTS` ou na mensagem). Sua tarefa é produzir um perfil completo da tabela e uma sugestão de chave primária.

### 1. Carregar o arquivo

```python
import pandas as pd
import json, re
from pathlib import Path

path = "<caminho_fornecido>"
try:
    df = pd.read_csv(path, sep=";", encoding="utf-8", dtype=str)
except UnicodeDecodeError:
    df = pd.read_csv(path, sep=";", encoding="latin-1", dtype=str)

# Se não parseou corretamente (1 única coluna), tentar vírgula
if len(df.columns) == 1:
    try:
        df = pd.read_csv(path, sep=",", encoding="utf-8", dtype=str)
    except Exception:
        pass
```

Leia tudo como string (`dtype=str`) para não perder zeros à esquerda — comum em códigos de órgão, UO, NE, CNPJ.

### 2. Perfilar cada coluna

Para cada coluna, calcule:

| Métrica | Como calcular |
|---|---|
| `dtype_original` | `df[col].dtype` antes de forçar str; ou infira pelo conteúdo |
| `unique_count` | `df[col].nunique()` |
| `null_rate` | `df[col].isna().mean()` |
| `uniqueness_rate` | `unique_count / len(df[col].dropna())` |
| `avg_length` | `df[col].dropna().str.len().mean()` |
| `top_5_values` | `df[col].value_counts().head(5).to_dict()` |

### 3. Detectar grupo de domínio

Normalize o nome da coluna (lower, substitua `.`, `-`, ` ` por `_`) e cheque os padrões abaixo. O primeiro match vence.

```python
DOMAIN_GROUPS = {
    "empenho":           ["nr_empenho", "num_empenho", "numero_empenho", "empenho", "cd_empenho", "ne", "nota_empenho"],
    "convenio":          ["nr_convenio", "num_convenio", "numero_convenio", "convenio", "cd_convenio"],
    "orgao":             ["cd_orgao", "cod_orgao", "codigo_orgao", "orgao", "nr_orgao", "id_orgao", "sg_orgao"],
    "unidade_orcamentaria": ["cd_uo", "cod_uo", "unidade_orcamentaria", "uo", "cd_unidade"],
    "programa":          ["cd_programa", "cod_programa", "codigo_programa", "programa"],
    "acao":              ["cd_acao", "cod_acao", "codigo_acao", "acao"],
    "funcao":            ["cd_funcao", "cod_funcao", "funcao"],
    "subfuncao":         ["cd_subfuncao", "cod_subfuncao", "subfuncao"],
    "fonte_recurso":     ["cd_fonte", "cod_fonte", "fonte_recurso", "fonte"],
    "natureza_despesa":  ["cd_natureza", "cod_natureza", "natureza_despesa", "nd", "elemento_despesa"],
    "instrumento":       ["nr_instrumento", "num_instrumento", "instrumento", "cd_instrumento"],
    "nota_credito":      ["nr_nc", "nota_credito", "nc", "num_nc"],
    "exercicio":         ["exercicio", "ano_exercicio", "ano", "cd_ano", "nr_exercicio"],
    "cpf_cnpj":          ["cpf", "cnpj", "cpf_cnpj", "nr_cpf", "nr_cnpj", "documento"],
    "municipio":         ["cd_municipio", "cod_municipio", "municipio", "ibge", "cd_ibge"],
    "uf":                ["uf", "sg_uf", "cd_uf", "estado"],
    "valor":             ["vl_", "valor", "vlr", "montante", "total", "saldo"],
}
```

Faça matching exato primeiro; depois matching parcial (nome da coluna contém o alias ou vice-versa).

### 4. Detectar padrões regex

Pegue uma amostra de 100 valores não-nulos e teste:

```python
PATTERNS = {
    "nota_empenho": r"^\d{4}NE\d{6}$",
    "convenio":     r"^\d{6}/\d{4}$",
    "cnpj_fmt":     r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$",
    "cnpj_raw":     r"^\d{14}$",
    "cpf_fmt":      r"^\d{3}\.\d{3}\.\d{3}-\d{2}$",
    "cpf_raw":      r"^\d{11}$",
    "codigo_5dig":  r"^\d{5}$",
    "codigo_6dig":  r"^\d{6}$",
    "exercicio":    r"^\d{4}$",
    "valor_br":     r"^\d{1,3}(\.\d{3})*(,\d{2})?$",
}
```

Reporte o padrão com > 80% de match na amostra. Se nenhum, reporte `null`.

### 5. Detectar distribuição de exercícios

Detecte se a tabela tem uma coluna de exercício fiscal e compute a distribuição de anos:

```python
from src.analyzers.exercicio_profiler import exercicio_distribution

# domain_groups: DOMAIN_GROUPS carregado na etapa 3
exercicio_dist = exercicio_distribution(df, domain_groups=DOMAIN_GROUPS)
# Retorna {"2022": 1500, "2023": 2000} ou None se não houver coluna de exercício
```

Se os módulos não estiverem disponíveis, execute inline:

```python
import re

def _detect_exercicio(df, domain_groups):
    aliases = {a.lower() for a in domain_groups.get("exercicio", [])}
    for col in df.columns:
        norm = re.sub(r"[^a-z0-9]", "_", col.lower().strip())
        if norm in aliases:
            series = df[col].dropna().astype(str)
            dist = series.value_counts().to_dict()
            return {k: int(v) for k, v in dist.items() if re.match(r"^\d{4}$", k)}
    for col in df.columns:
        series = df[col].dropna().astype(str)
        if len(series) == 0:
            continue
        if series.str.match(r"^\d{4}$").sum() / len(series) >= 0.80:
            try:
                years = series[series.str.match(r"^\d{4}$")].astype(int)
                if years.between(1990, 2040).all():
                    dist = series.value_counts().to_dict()
                    return {k: int(v) for k, v in dist.items() if re.match(r"^\d{4}$", k)}
            except Exception:
                pass
    return None

exercicio_dist = _detect_exercicio(df, DOMAIN_GROUPS)
```

### 6. Identificar candidatas a chave primária

Uma coluna é candidata se:
- `uniqueness_rate >= 0.95`
- `null_rate <= 0.02`

Ordene as candidatas por `uniqueness_rate` decrescente.

### 7. Sugerir a melhor chave

Use o seguinte critério de desempate:
1. Candidata com grupo de domínio reconhecido tem prioridade
2. Candidata com padrão regex identificado tem prioridade
3. Em caso de empate, a de maior `uniqueness_rate`

Justifique sua escolha em 1-2 frases.

### 8. Exibir no terminal

```
======================================================================
PERFIL DA TABELA: <nome_do_arquivo>
Linhas: X | Colunas: Y
======================================================================

COLUNAS:
  <col>  [grupo: <grupo>] [padrão: <padrão>]
    dtype          : <tipo>
    únicos         : <N> (<uniqueness_rate:.1%>)
    nulos          : <null_rate:.1%>
    comp. médio    : <avg_length:.1f> chars
    top valores    : <val1> (<N>x), <val2> (<N>x), ...

...

CANDIDATAS A CHAVE PRIMÁRIA:
  ✓ <col> — uniqueness: <rate:.1%>, grupo: <grupo>, padrão: <padrão>
  ...

SUGESTÃO DE CHAVE: <col>
  "<justificativa>"
======================================================================
```

### 9. Salvar JSON

Salve em `/home/luiza-maluf/Área de trabalho/tcc/fase01/output/analisar_tabela_<nome_sem_extensao>.json`:

```json
{
  "table_name": "",
  "row_count": 0,
  "column_count": 0,
  "columns": [
    {
      "name": "",
      "unique_count": 0,
      "null_rate": 0.0,
      "uniqueness_rate": 0.0,
      "avg_length": 0.0,
      "top_values": {},
      "domain_group": null,
      "detected_pattern": null
    }
  ],
  "primary_key_candidates": [],
  "suggested_key": "",
  "suggested_key_justification": "",
  "exercicio_distribution": null
}
```

Crie o diretório `output/` dentro de `PROJECT_ROOT` se não existir. Informe o caminho completo do arquivo ao final.

## Cuidados importantes

- **Zeros à esquerda importam.** Código de órgão `00001` é diferente de `1`. Por isso leia tudo como string.
- **Encoding é frequentemente problema.** Bases do SIAFI e Portal da Transparência vêm em `latin-1`.
- **Separador pode ser vírgula.** Tente `;` primeiro, depois `,`.
- **Valores monetários** em formato brasileiro (`1.234,56`) devem ser identificados como `valor_br`, não como número.
- **Colunas com nome genérico** (ex: `campo1`, `col_a`) podem ainda ter grupo detectável pelo padrão dos valores — priorize o padrão nesses casos.
