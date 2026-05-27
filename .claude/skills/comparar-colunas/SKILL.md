---
name: comparar-colunas
description: Evidence Layer do Integration Pipeline — compara pares de colunas entre duas tabelas e coleta evidências de compatibilidade (match rate bidirecional, padrões, dtype, cardinalidade, transformações necessárias). Opera em dois modos: automático (invocado pelo integrar-bases, seleciona pares a partir dos JSONs do analisar-tabela) e manual (usuário especifica duas colunas para testar uma hipótese). Use SEMPRE que o usuário quiser saber se duas colunas "casam", se um join vai funcionar, ou quando quiser testar uma hipótese de chave antes de rodar o pipeline completo. Também disparar quando o usuário disser "será que esse campo bate com aquele?", "testa essa coluna contra aquela", "verifica se dá pra joinear por X".
input:
  - type: json
    path: output/analisar_tabela_{table_a}.json
    description: Perfil da tabela A — usado no modo automático
    optional: true
  - type: json
    path: output/analisar_tabela_{table_b}.json
    description: Perfil da tabela B — usado no modo automático
    optional: true
  - type: csv
    path: "{table_a}:{col_a}"
    description: Coluna específica — usado no modo manual
    optional: true
  - type: csv
    path: "{table_b}:{col_b}"
    description: Coluna específica — usado no modo manual
    optional: true
  - type: json
    path: "output/contexts/context_{domain}.json"
    description: Domain Context (opcional)
    optional: true
output:
  - type: json
    path: output/comparar_colunas_{table_a}__{table_b}.json
    description: Modo automático — todos os pares avaliados
  - type: json
    path: output/comparar_colunas_{table_a}_{col_a}__{table_b}_{col_b}.json
    description: Modo manual — par específico
---

## Contexto do projeto

```
PROJECT_ROOT = /home/luiza-maluf/Área de trabalho/tcc/fase01
```

Módulos disponíveis:
```python
import sys
sys.path.insert(0, "/home/luiza-maluf/Área de trabalho/tcc/fase01")
```

- `src.analyzers.statistical` — `match_rate`, `overlap_stats`
- `src.analyzers.semantic` — `semantic_score`, `find_domain_group`
- `src.transformers.normalizer` — `normalize_series`
- `src.transformers.pattern_detector` — `detect_pattern`
- `src.config.context_loader` — `load_context`

JSON de saída:
- Modo automático: `output/comparar_colunas_{stem_a}__{stem_b}.json`
- Modo manual: `output/comparar_colunas_{stem_a}_{col_a}__{stem_b}_{col_b}.json`

---

## Modo de operação

**Modo automático** — acionado pelo `integrar-bases` ou quando o usuário fornece dois JSONs de perfil sem especificar colunas.
**Modo manual** — acionado quando o usuário especifica colunas explicitamente (`arquivo.csv:coluna`).

---

## MODO AUTOMÁTICO — Evidence Layer

### 1. Carregar perfis e contexto

```python
import json
from pathlib import Path
from src.config.context_loader import load_context

profile_a = json.loads(Path("output/analisar_tabela_{stem_a}.json").read_text())
profile_b = json.loads(Path("output/analisar_tabela_{stem_b}.json").read_text())
context = load_context(context_path)  # None para defaults
```

### 2. Selecionar pares candidatos

Selecione pares para comparar usando os critérios abaixo (em ordem de prioridade):

**Critério 1 — Cruzamento de primary key candidates:**
```python
pk_a = [c["name"] for c in profile_a["primary_key_candidates"]]
pk_b = [c["name"] for c in profile_b["primary_key_candidates"]]
pairs = [(a, b) for a in pk_a for b in pk_b]
```

**Critério 2 — Mesmo grupo de domínio:**
```python
from src.analyzers.semantic import find_domain_group

for col_a in profile_a["columns"]:
    for col_b in profile_b["columns"]:
        g_a = find_domain_group(col_a["name"])
        g_b = find_domain_group(col_b["name"])
        if g_a and g_a == g_b and (col_a["name"], col_b["name"]) not in pairs:
            pairs.append((col_a["name"], col_b["name"]))
```

**Critério 3 — Score semântico ≥ 0.30:**
```python
from src.analyzers.semantic import semantic_score

for col_a in profile_a["columns"]:
    for col_b in profile_b["columns"]:
        if semantic_score(col_a["name"], col_b["name"]) >= 0.30:
            pair = (col_a["name"], col_b["name"])
            if pair not in pairs:
                pairs.append(pair)
```

Limite a top-15 pares ordenados por score semântico antes de calcular match rate.

### 3. Comparar cada par

Para cada par selecionado, execute a análise completa (match rate, perfis, padrões, evidências) conforme o Modo Manual descrito abaixo. Carregue as colunas dos CSVs originais (paths em `profile_a["table_name"]` e `profile_b["table_name"]`).

### 4. Salvar output consolidado

```json
{
  "table_a": "{stem_a}",
  "table_b": "{stem_b}",
  "domain_context": "{domain_name}",
  "pairs_evaluated": 0,
  "pairs": [
    {
      "col_a": "",
      "col_b": "",
      "match_rate_normalized": { "a_in_b": 0.0, "b_in_a": 0.0 },
      "semantic_score": 0.0,
      "domain_group_a": null,
      "domain_group_b": null,
      "detected_pattern_a": null,
      "detected_pattern_b": null,
      "verdict": "COMPATÍVEL | PARCIALMENTE COMPATÍVEL | INCOMPATÍVEL",
      "evidence_for": [],
      "evidence_against": [],
      "required_transformations": []
    }
  ]
}
```

---

## MODO MANUAL

### Entrada esperada

O usuário fornece em `$ARGUMENTS` ou na mensagem:

```
<arquivo_a.csv>:<coluna_a>  <arquivo_b.csv>:<coluna_b>
```

Exemplos:
```
data/raw/empenhos.csv:nr_empenho  data/raw/pagamentos.csv:num_empenho
data/raw/notas.csv:cd_orgao  data/raw/convenios.csv:CO_ORGAO
```

Se o usuário não usar o formato com `:`, interprete pelo contexto — ele pode dizer "compara `nr_empenho` da tabela de empenhos com `numero_ne` da tabela de pagamentos".

---

## O que fazer

### 1. Carregar as colunas

Carregue apenas a coluna relevante de cada CSV (use `usecols` para eficiência). Tente `utf-8` e faça fallback para `latin-1`. Leia como `dtype=str` para preservar zeros à esquerda.

```python
import pandas as pd
from pathlib import Path

def load_col(path, col):
    try:
        return pd.read_csv(path, sep=";", encoding="utf-8", dtype=str, usecols=[col])[col]
    except UnicodeDecodeError:
        return pd.read_csv(path, sep=";", encoding="latin-1", dtype=str, usecols=[col])[col]
```

Se o separador `;` não funcionar, tente `,`.

### 2. Perfil individual de cada coluna

Para cada coluna:

| Métrica | Cálculo |
|---|---|
| `total_rows` | `len(series)` |
| `unique_count` | `series.nunique()` |
| `null_rate` | `series.isna().mean()` |
| `uniqueness_rate` | `unique_count / len(series.dropna())` |
| `avg_length` | `series.dropna().str.len().mean()` |
| `top_5_values` | `series.value_counts().head(5).to_dict()` |
| `domain_group` | via `find_domain_group()` ou tabela DOMAIN_GROUPS do analisar-tabela |
| `detected_pattern` | via `detect_pattern()` ou PATTERNS do analisar-tabela |

### 3. Normalizar e calcular match rate

Normalize ambas as séries antes de comparar — isso evita falsos negativos por diferença de case, espaços ou pontuação:

```python
def normalize(s):
    return s.astype(str).str.strip().str.upper().str.replace(r"[.\-/\s]", "", regex=True)

s_a_norm = normalize(col_a.dropna())
s_b_norm = normalize(col_b.dropna())

set_b = set(s_b_norm.unique())
match_a_in_b = s_a_norm.isin(set_b).mean()   # % de A que existe em B
match_b_in_a = s_b_norm.isin(set(s_a_norm.unique())).mean()  # % de B que existe em A
```

Colete também:
- **Exemplos que casam** (5 valores presentes em ambas)
- **Exemplos que não casam** de A (5 valores de A ausentes em B)
- **Exemplos que não casam** de B (5 valores de B ausentes em A)

### 4. Score semântico entre os nomes

Compare os nomes das colunas usando `semantic_score()` ou diretamente com `difflib.SequenceMatcher`. Um score alto (> 0.7) reforça a hipótese; um score baixo não a descarta sozinho.

### 5. Detectar transformações necessárias

Identifique automaticamente o que precisa ser feito para o join funcionar:

| Situação | Transformação sugerida |
|---|---|
| Comprimento médio difere em > 2 chars | Verificar padding (zfill) ou truncamento |
| Match sobe após normalizar | `strip + upper + remove_special_chars` |
| Um tem `14` dígitos, outro tem `XX.XXX.XXX/XXXX-XX` | Remover pontuação do CNPJ formatado |
| Valores de A com zeros à esquerda ausentes em B | `lstrip('0')` ou `zfill(N)` |
| Dtype incompatível | Cast explícito antes do join |

Para detectar o efeito das transformações, compare o match_rate antes e depois da normalização — se subiu, a normalização é necessária.

### 6. Emitir o veredito

| Critério | Veredito |
|---|---|
| match_rate (média A↔B) ≥ 0.80 e grupos de domínio compatíveis | **COMPATÍVEL** |
| match_rate ≥ 0.50 ou grupos compatíveis mas match baixo | **PARCIALMENTE COMPATÍVEL** |
| match_rate < 0.50 e domínios incompatíveis | **INCOMPATÍVEL** |

O veredito deve considerar também: se o match sobe muito com normalização, considere COMPATÍVEL mesmo que o raw seja baixo.

### 7. Exibir no terminal

```
══════════════════════════════════════════════════════════════════════
COMPARAÇÃO DE COLUNAS
  Tabela A : <arquivo_a> → coluna: <col_a>
  Tabela B : <arquivo_b> → coluna: <col_b>
══════════════════════════════════════════════════════════════════════

                        COL_A              COL_B
  Linhas              : X                  Y
  Únicos              : X (XX.X%)          Y (YY.Y%)
  Nulos               : X.X%              Y.Y%
  Comp. médio         : X.X chars         Y.Y chars
  Grupo de domínio    : <grupo>           <grupo>
  Padrão detectado    : <padrão>          <padrão>

MATCH RATE (após normalização):
  A → B : XX.X%   (X de Y valores de A encontrados em B)
  B → A : XX.X%   (X de Y valores de B encontrados em A)

Score semântico entre nomes: X.XX

EXEMPLOS QUE CASAM    : val1, val2, val3...
EXEMPLOS SÓ EM A      : val1, val2, val3...
EXEMPLOS SÓ EM B      : val1, val2, val3...

TRANSFORMAÇÕES SUGERIDAS:
  • <transformação 1>
  • <transformação 2>

══════════════════════════════════════════════════════════════════════
VEREDITO: ✅ COMPATÍVEL | ⚠️ PARCIALMENTE COMPATÍVEL | ❌ INCOMPATÍVEL
  "<justificativa em 1-2 frases>"
══════════════════════════════════════════════════════════════════════
```

### 8. Salvar JSON

```json
{
  "table_a": { "file": "", "column": "" },
  "table_b": { "file": "", "column": "" },
  "profile_a": {
    "total_rows": 0, "unique_count": 0, "null_rate": 0.0,
    "uniqueness_rate": 0.0, "avg_length": 0.0,
    "top_values": {}, "domain_group": null, "detected_pattern": null
  },
  "profile_b": { "...": "mesmo formato" },
  "match_rate_raw": { "a_in_b": 0.0, "b_in_a": 0.0 },
  "match_rate_normalized": { "a_in_b": 0.0, "b_in_a": 0.0 },
  "sample_matches": [],
  "sample_only_in_a": [],
  "sample_only_in_b": [],
  "semantic_score": 0.0,
  "required_transformations": [],
  "verdict": "COMPATÍVEL | PARCIALMENTE COMPATÍVEL | INCOMPATÍVEL",
  "justification": ""
}
```

---

## Cuidados importantes

- **Não descarte uma hipótese só pelo match_rate raw.** Bases governamentais frequentemente têm diferenças de formatação (CNPJ com e sem pontuação, códigos com e sem zeros). Sempre compare raw vs normalizado.
- **Match rate baixo pode ser correto.** Se tabela B é um subconjunto de A (ex: apenas empenhos pagos), o match de B→A pode ser 100% enquanto A→B é baixo. Interprete direcionalmente.
- **Grupos de domínio incompatíveis são sinal forte de incompatibilidade**, mesmo que o match rate seja acidentalmente alto (ex: dois campos numéricos de domínios diferentes podem ter valores coincidentes).
- **Nomes de coluna em maiúsculo** (CO_ORGAO) ou com prefixo diferente (nr_ vs num_ vs cd_) são comuns e não indicam incompatibilidade — o score semântico e o match rate são mais confiáveis que o nome isolado.
