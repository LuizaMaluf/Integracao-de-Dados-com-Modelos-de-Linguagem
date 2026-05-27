---
name: comparar-dados
description: Content Evidence Layer — compara valores reais entre duas tabelas CSV para encontrar Candidate Keys em pares onde a semelhança de nome de coluna é baixa (score semântico < 0.45). Detecta format match (mesmo padrão regex dominante), sobreposição de valores e relações de substring que indicam Derived Keys. Produz CandidateKeys com content_score para o identificar-chave. Use quando o mapear-integracoes rejeitar um par por baixa afinidade semântica, quando suspeitar que colunas com nomes não relacionados contêm os mesmos dados, ou para testar hipóteses pontuais de integração por conteúdo.
input:
  - type: csv
    path: "{table_a}"
    description: Primeira tabela (obrigatório)
  - type: csv
    path: "{table_b}"
    description: Segunda tabela (obrigatório)
  - type: json
    path: "output/analisar_tabela_{stem_a}.json"
    description: Perfil da tabela A gerado pelo analisar-tabela (opcional — melhora alinhamento temporal)
    optional: true
  - type: json
    path: "output/analisar_tabela_{stem_b}.json"
    description: Perfil da tabela B gerado pelo analisar-tabela (opcional)
    optional: true
output:
  - type: json
    path: output/comparar_dados_{stem_a}__{stem_b}.json
---

## Contexto do projeto

```
PROJECT_ROOT = /home/luiza-maluf/Área de trabalho/tcc/fase01
```

Módulos disponíveis:
```python
import sys
sys.path.insert(0, PROJECT_ROOT)

from src.analyzers.content_analyzer import analyze, PROMOTION_THRESHOLD
from src.analyzers.exercicio_profiler import exercicio_distribution
from src.analyzers.structural import dtype_compatible
from src.config.context_loader import load_context
```

---

## O que fazer

### Etapa 0 — Carregar as tabelas

```python
import pandas as pd
from pathlib import Path

def load_csv(path):
    try:
        return pd.read_csv(path, sep=";", encoding="utf-8", dtype=str)
    except Exception:
        return pd.read_csv(path, sep=",", encoding="latin-1", dtype=str)

df_a = load_csv(table_a)
df_b = load_csv(table_b)
stem_a = Path(table_a).stem
stem_b = Path(table_b).stem
```

### Etapa 1 — Alinhar exercícios (se perfis disponíveis)

Se os JSONs de perfil existirem, leia a interseção de exercícios e filtre os DataFrames:

```python
import json

profile_a_path = Path(f"output/analisar_tabela_{stem_a}.json")
profile_b_path = Path(f"output/analisar_tabela_{stem_b}.json")

exercicio_col_a = None
exercicio_col_b = None
common_exercicios = None

if profile_a_path.exists() and profile_b_path.exists():
    prof_a = json.loads(profile_a_path.read_text())
    prof_b = json.loads(profile_b_path.read_text())
    dist_a = prof_a.get("exercicio_distribution") or {}
    dist_b = prof_b.get("exercicio_distribution") or {}

    common = set(dist_a.keys()) & set(dist_b.keys())
    if common:
        common_exercicios = sorted(common)
        # Detectar qual coluna é o exercício em cada DF
        from src.analyzers.exercicio_profiler import detect_exercicio_column
        exercicio_col_a = detect_exercicio_column(df_a)
        exercicio_col_b = detect_exercicio_column(df_b)

        if exercicio_col_a:
            df_a = df_a[df_a[exercicio_col_a].astype(str).isin(common)]
        if exercicio_col_b:
            df_b = df_b[df_b[exercicio_col_b].astype(str).isin(common)]

        print(f"  Exercícios em comum: {common_exercicios} → {len(df_a)} linhas em A, {len(df_b)} linhas em B")
    else:
        print("  Sem exercícios em comum — usando tabelas completas")
```

Se os perfis não existirem, use os DataFrames completos sem filtro.

### Etapa 2 — Pré-filtro por dtype e geração de pares

```python
from src.analyzers.structural import dtype_compatible

pairs_to_evaluate = []
for col_a in df_a.columns:
    for col_b in df_b.columns:
        dtype_a = str(df_a[col_a].dtype)
        dtype_b = str(df_b[col_b].dtype)
        if dtype_compatible(dtype_a, dtype_b):
            pairs_to_evaluate.append((col_a, col_b))

print(f"  {len(df_a.columns)} × {len(df_b.columns)} = {len(df_a.columns)*len(df_b.columns)} pares totais")
print(f"  {len(pairs_to_evaluate)} pares passaram o pré-filtro de dtype")
```

### Etapa 3 — Análise de conteúdo por par

```python
from src.analyzers.content_analyzer import analyze, PROMOTION_THRESHOLD

results = []
promoted = []

for col_a, col_b in pairs_to_evaluate:
    evidence = analyze(df_a[col_a], df_b[col_b])
    entry = {
        "col_a": col_a,
        "col_b": col_b,
        **evidence.to_dict(),
    }
    results.append(entry)
    if evidence.promoted():
        promoted.append(entry)

results.sort(key=lambda x: x["content_score"], reverse=True)
promoted.sort(key=lambda x: x["content_score"], reverse=True)
```

### Etapa 4 — Exibir resultado no terminal

```
══════════════════════════════════════════════════════════════════════
COMPARAÇÃO DE DADOS: {stem_a} × {stem_b}
  Pares avaliados  : {len(results)}
  Pares promovidos : {len(promoted)} (content_score ≥ {PROMOTION_THRESHOLD})
══════════════════════════════════════════════════════════════════════

CANDIDATOS PROMOVIDOS:
  {col_a} ↔ {col_b}
    content_score    : {content_score:.3f}
    format_match     : {format_match} ({format_a} / {format_b})
    overlap_rate     : {overlap_rate:.1%}
    substring_match  : {substring_match_rate:.1%}
  ...

TOP-10 PARES (incluindo não promovidos):
  {col_a:<30} ↔ {col_b:<30}  score={content_score:.3f}
  ...
══════════════════════════════════════════════════════════════════════
```

Se `len(promoted) == 0`:
```
Nenhum par atingiu content_score ≥ {PROMOTION_THRESHOLD}.
Top par encontrado: {col_a} ↔ {col_b} (score={content_score:.3f})
```

### Etapa 5 — Salvar JSON e encaminhar ao identificar-chave

```python
import json
from datetime import date
from pathlib import Path

output = {
    "table_a": stem_a,
    "table_b": stem_b,
    "date": date.today().isoformat(),
    "exercicios_alinhados": common_exercicios,
    "pairs_evaluated": len(results),
    "promotion_threshold": PROMOTION_THRESHOLD,
    "promoted_count": len(promoted),
    "all_pairs": results,
}

out_path = Path(f"output/comparar_dados_{stem_a}__{stem_b}.json")
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
print(f"\nSalvo em: {out_path}")
```

Se `len(promoted) > 0`, execute a lógica do `identificar-chave` passando os candidatos promovidos como Evidence Layer, com `discovery_method: "content"` adicionado a cada candidato:

```python
for p in promoted:
    p["discovery_method"] = "content"
    p["evidence_for"] = []
    if p["format_match"]:
        p["evidence_for"].append(f"Mesmo formato dominante: {p['format_a']}")
    if p["overlap_rate"] >= 0.5:
        p["evidence_for"].append(f"Sobreposição direta de valores: {p['overlap_rate']:.1%}")
    if p["substring_match_rate"] >= 0.5:
        p["evidence_for"].append(f"Relação de substring detectada: {p['substring_match_rate']:.1%} — possível Derived Key")
```

---

## Cuidados

- Nunca usar semelhança de nome de coluna como sinal — este é o caminho semântico. A skill opera exclusivamente sobre os valores.
- Se ambas as colunas tiverem mais de 80% de nulos no sample, pular o par sem computar.
- O alinhamento de exercícios é melhor-esforço: se os perfis não existirem, a skill funciona sem ele, mas o content_score pode ser artificialmente baixo por diferença de período.
- Normalize o `stem`: lowercase, substitua espaços e caracteres especiais por `_`.
