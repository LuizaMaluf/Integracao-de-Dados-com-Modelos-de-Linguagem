---
name: mapear-integracoes
description: Descobre automaticamente quais bases de um diretório podem ser integradas entre si. Analisa todos os arquivos CSV do diretório, calcula score semântico entre todos os pares possíveis, filtra os pares com potencial de integração e executa o pipeline completo apenas nesses pares — evitando 28 execuções desnecessárias quando só 4 fazem sentido. Gera um mapa HTML de integrações mostrando quais bases se conectam a quais e com qual confiança. Use quando o usuário quiser explorar um diretório de bases, descobrir quais arquivos têm relação entre si, ou rodar o pipeline em lote sem especificar pares manualmente. Disparar quando o usuário disser "integra tudo desse diretório", "quais bases se relacionam?", "mapeie as integrações", ou fornecer um caminho de diretório.
input:
  - type: directory
    path: "{diretorio}"
    description: Diretório contendo os CSVs a mapear (obrigatório)
  - type: json
    path: "output/contexts/context_{domain}.json"
    description: Domain Context (opcional)
    optional: true
output:
  - type: json
    path: output/mapa_integracoes_{dir_stem}_{date}.json
  - type: html
    path: output/reports/mapa_integracoes_{dir_stem}_{date}.html
  - type: html
    path: "output/reports/relatorio_{a}__{b}_{date}.html (um por par aprovado)"
---

## Contexto do projeto

```
PROJECT_ROOT = /home/luiza-maluf/Área de trabalho/tcc/fase01
```

Módulos disponíveis:
```python
import sys
sys.path.insert(0, "/home/luiza-maluf/Área de trabalho/tcc/fase01")
from src.analyzers.semantic import semantic_score, find_domain_group
from src.config.context_loader import load_context
```

---

## O que fazer

### Etapa 0 — Listar e carregar arquivos

```python
from pathlib import Path
import pandas as pd

dir_path = Path("{diretorio}")
csv_files = sorted(dir_path.glob("*.csv"))

if len(csv_files) < 2:
    print("Diretório precisa ter ao menos 2 arquivos CSV.")
    exit()

print(f"Encontrados {len(csv_files)} arquivos → {len(csv_files)*(len(csv_files)-1)//2} pares possíveis")
```

Exibir:
```
══════════════════════════════════════════════════════════════════════
MAPEAMENTO DE INTEGRAÇÕES
  Diretório : {diretorio}
  Arquivos  : {N} CSVs encontrados
  Pares     : {C(N,2)} combinações possíveis
══════════════════════════════════════════════════════════════════════
```

### Etapa 1 — Perfil rápido de cada arquivo

Para cada CSV, extraia apenas os nomes das colunas (sem ler o arquivo inteiro):

```python
def get_columns(path):
    try:
        return list(pd.read_csv(path, sep=";", encoding="utf-8", nrows=0, dtype=str).columns)
    except Exception:
        return list(pd.read_csv(path, sep=",", encoding="latin-1", nrows=0, dtype=str).columns)

table_columns = {f.stem: get_columns(f) for f in csv_files}
```

### Etapa 2 — Score semântico entre todos os pares

Para cada par `(a, b)`, calcule o **score de afinidade do par**: média dos scores semânticos dos top-3 pares de colunas mais similares entre as duas tabelas.

```python
from itertools import combinations
from src.analyzers.semantic import semantic_score

CANDIDATE_THRESHOLD = 0.45  # pares abaixo disso são descartados

pair_scores = []

for (name_a, cols_a), (name_b, cols_b) in combinations(table_columns.items(), 2):
    # score semântico dos top-3 pares de colunas
    col_scores = sorted(
        [semantic_score(ca, cb) for ca in cols_a for cb in cols_b],
        reverse=True
    )
    top3_avg = sum(col_scores[:3]) / 3 if col_scores else 0.0

    # boost: verifica se algum par de colunas compartilha grupo de domínio
    from src.analyzers.semantic import find_domain_group
    shared_groups = sum(
        1 for ca in cols_a for cb in cols_b
        if find_domain_group(ca) and find_domain_group(ca) == find_domain_group(cb)
    )
    group_boost = min(shared_groups * 0.1, 0.2)

    affinity = min(top3_avg + group_boost, 1.0)

    pair_scores.append({
        "table_a": name_a,
        "table_b": name_b,
        "affinity": round(affinity, 3),
        "shared_domain_groups": shared_groups,
        "top_col_score": round(col_scores[0], 3) if col_scores else 0.0,
    })

pair_scores.sort(key=lambda x: x["affinity"], reverse=True)
```

### Etapa 3 — Filtrar pares com potencial

```python
approved = [p for p in pair_scores if p["affinity"] >= CANDIDATE_THRESHOLD]
skipped  = [p for p in pair_scores if p["affinity"] <  CANDIDATE_THRESHOLD]

print(f"\nPares aprovados para pipeline completo : {len(approved)}")
print(f"Pares descartados (afinidade < {CANDIDATE_THRESHOLD}): {len(skipped)}")
```

Se `len(approved) == 0`, reduza o limiar para 0.30 e informe o usuário.

Se `len(approved) > 10`, pergunte ao usuário se deseja processar todos ou apenas os top-10.

### Etapa 4 — Pipeline completo nos pares aprovados

Para cada par aprovado, execute o pipeline de `/integrar-bases` (etapas 1–4: analisar, comparar, identificar, relatar).

Exibir progresso:
```
[1/{total}] {table_a} × {table_b}  (afinidade: {affinity:.2f})
  → analisando...
  → comparando colunas...
  → identificando chave...
  → gerando relatório...
  ✓ Integration Key: {col_a} ↔ {col_b}  confiança: {confidence:.2f}

[2/{total}] ...
```

Colete os resultados de cada par:
```python
results = []
for p in approved:
    # ... executa pipeline ...
    results.append({
        "table_a": p["table_a"],
        "table_b": p["table_b"],
        "affinity": p["affinity"],
        "integration_key": {"col_a": ..., "col_b": ..., "confidence": ...},
        "report_path": "output/reports/relatorio_{a}__{b}_{date}.html",
    })
```

### Etapa 4b — Content Evidence pass nos pares rejeitados

Após a Etapa 4, execute a lógica do `comparar-dados` para cada par em `skipped`:

```python
from src.analyzers.content_analyzer import analyze, PROMOTION_THRESHOLD
from src.analyzers.structural import dtype_compatible

content_recovered = []

print(f"\n[Content Evidence Pass] Analisando {len(skipped)} pares rejeitados...")

for p in skipped:
    name_a, name_b = p["table_a"], p["table_b"]
    path_a = next(f for f in csv_files if f.stem == name_a)
    path_b = next(f for f in csv_files if f.stem == name_b)

    try:
        df_a = load_csv(path_a)  # reuse a função load_csv definida acima
        df_b = load_csv(path_b)

        # Alinhar exercícios se perfis existirem
        prof_a_path = Path(f"output/analisar_tabela_{name_a}.json")
        prof_b_path = Path(f"output/analisar_tabela_{name_b}.json")
        if prof_a_path.exists() and prof_b_path.exists():
            from src.analyzers.exercicio_profiler import detect_exercicio_column
            prof_a = json.loads(prof_a_path.read_text())
            prof_b = json.loads(prof_b_path.read_text())
            dist_a = prof_a.get("exercicio_distribution") or {}
            dist_b = prof_b.get("exercicio_distribution") or {}
            common = set(dist_a.keys()) & set(dist_b.keys())
            if common:
                ecol_a = detect_exercicio_column(df_a)
                ecol_b = detect_exercicio_column(df_b)
                if ecol_a:
                    df_a = df_a[df_a[ecol_a].astype(str).isin(common)]
                if ecol_b:
                    df_b = df_b[df_b[ecol_b].astype(str).isin(common)]

        # Pré-filtro por dtype + análise de conteúdo
        best_score = 0.0
        best_pair = None
        promoted_pairs = []

        for col_a in df_a.columns:
            for col_b in df_b.columns:
                if not dtype_compatible(str(df_a[col_a].dtype), str(df_b[col_b].dtype)):
                    continue
                evidence = analyze(df_a[col_a], df_b[col_b])
                if evidence.content_score > best_score:
                    best_score = evidence.content_score
                    best_pair = (col_a, col_b, evidence)
                if evidence.promoted():
                    promoted_pairs.append((col_a, col_b, evidence))

        if promoted_pairs:
            # Executa pipeline completo nos pares promovidos (integrar-bases)
            # e registra com discovery_method: "content"
            col_a, col_b, ev = promoted_pairs[0]  # melhor par promovido
            print(f"  ✓ {name_a} × {name_b} — par recuperado: {col_a} ↔ {col_b} (content_score={ev.content_score:.3f})")
            content_recovered.append({
                "table_a": name_a,
                "table_b": name_b,
                "affinity": p["affinity"],
                "content_score": ev.content_score,
                "discovery_method": "content",
                "integration_key": {
                    "col_a": col_a,
                    "col_b": col_b,
                    "format_match": ev.format_match,
                    "overlap_rate": ev.overlap_rate,
                    "substring_match_rate": ev.substring_match_rate,
                },
                "promoted_pairs_count": len(promoted_pairs),
            })
        else:
            best_info = f"{best_pair[0]} ↔ {best_pair[1]} (score={best_score:.3f})" if best_pair else "nenhum"
            print(f"  · {name_a} × {name_b} — sem promoção. Melhor: {best_info}")

    except Exception as exc:
        print(f"  ✗ {name_a} × {name_b} — erro: {exc}")

print(f"\n[Content Evidence Pass] {len(content_recovered)} pares recuperados por conteúdo")
```

### Etapa 5 — Salvar mapa JSON

```python
import json
from datetime import date

mapa = {
    "directory": str(dir_path),
    "date": date.today().isoformat(),
    "tables": list(table_columns.keys()),
    "pairs_evaluated": len(pair_scores),
    "pairs_approved": len(approved),
    "pairs_skipped": len(skipped),
    "pairs_recovered_by_content": len(content_recovered),
    "threshold": CANDIDATE_THRESHOLD,
    "integrations": results,
    "content_integrations": content_recovered,
    "skipped_pairs": [p for p in skipped if p["table_a"] + "__" + p["table_b"]
                      not in {r["table_a"] + "__" + r["table_b"] for r in content_recovered}],
}

out_path = Path(f"output/mapa_integracoes_{dir_path.stem}_{date.today().isoformat()}.json")
out_path.write_text(json.dumps(mapa, indent=2, ensure_ascii=False))
```

### Etapa 6 — Gerar mapa HTML

Gere uma página HTML com CSS embutido mostrando o mapa de integrações:

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Mapa de Integrações — {dir_stem}</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 15px; line-height: 1.6; color: #1a1a2e; background: #f4f6fb; }
    .page { max-width: 1000px; margin: 0 auto; padding: 2rem 1.5rem 4rem; }

    header { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%); color: #fff; border-radius: 12px; padding: 2.5rem 2rem; margin-bottom: 2rem; }
    header h1 { font-size: 1.5rem; font-weight: 700; }
    header .sub { opacity: .7; font-size: .9rem; margin-top: .3rem; }
    .stats { display: flex; gap: 1rem; margin-top: 1.5rem; flex-wrap: wrap; }
    .stat { background: rgba(255,255,255,.1); border-radius: 8px; padding: .6rem 1rem; }
    .stat .val { font-size: 1.4rem; font-weight: 800; }
    .stat .lbl { font-size: .7rem; opacity: .7; text-transform: uppercase; letter-spacing: .05em; }

    section { background: #fff; border-radius: 12px; padding: 1.75rem 2rem; margin-bottom: 1.5rem; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
    section h2 { font-size: 1rem; font-weight: 700; color: #0f3460; margin-bottom: 1.25rem; padding-bottom: .5rem; border-bottom: 2px solid #eef2ff; }

    /* Integration cards */
    .cards { display: flex; flex-direction: column; gap: 1rem; }
    .card { border: 1px solid #e5e7eb; border-radius: 10px; padding: 1.25rem; display: grid; grid-template-columns: 1fr auto; align-items: start; gap: 1rem; }
    .card:hover { border-color: #4f46e5; background: #fafbff; }
    .card-title { font-weight: 700; font-size: .95rem; }
    .card-key { font-family: monospace; font-size: .85rem; background: #eef2ff; color: #4338ca; padding: .2rem .6rem; border-radius: 5px; margin-top: .3rem; display: inline-block; }
    .card-meta { font-size: .8rem; color: #6b7280; margin-top: .4rem; }

    .conf-pill { border-radius: 99px; padding: .25rem .75rem; font-size: .8rem; font-weight: 700; white-space: nowrap; }
    .conf-high   { background: #dcfce7; color: #166534; }
    .conf-medium { background: #fef9c3; color: #854d0e; }
    .conf-low    { background: #fee2e2; color: #991b1b; }

    .aff-bar-wrap { display: flex; align-items: center; gap: .5rem; margin-top: .5rem; }
    .aff-bar { flex: 1; height: 5px; background: #e5e7eb; border-radius: 3px; overflow: hidden; }
    .aff-fill { height: 100%; border-radius: 3px; background: #4f46e5; }
    .aff-num { font-size: .75rem; color: #6b7280; min-width: 32px; text-align: right; }

    .report-link { display: inline-block; margin-top: .75rem; font-size: .82rem; color: #4f46e5; text-decoration: none; }
    .report-link:hover { text-decoration: underline; }

    /* Skipped table */
    .skip-table { width: 100%; border-collapse: collapse; font-size: .85rem; }
    .skip-table th { background: #f8faff; color: #6b7280; font-size: .72rem; text-transform: uppercase; letter-spacing: .05em; padding: .5rem .75rem; text-align: left; border-bottom: 2px solid #e5e7eb; }
    .skip-table td { padding: .5rem .75rem; border-bottom: 1px solid #f3f4f6; color: #9ca3af; }
    .skip-table tr:last-child td { border-bottom: none; }

    footer { text-align: center; color: #9ca3af; font-size: .8rem; margin-top: 3rem; }
  </style>
</head>
<body>
<div class="page">

  <header>
    <h1>Mapa de Integrações</h1>
    <div class="sub">{dir_stem} · {date}</div>
    <div class="stats">
      <div class="stat"><div class="val">{N_tables}</div><div class="lbl">tabelas</div></div>
      <div class="stat"><div class="val">{N_pairs_total}</div><div class="lbl">pares possíveis</div></div>
      <div class="stat"><div class="val">{N_approved}</div><div class="lbl">pares integrados</div></div>
      <div class="stat"><div class="val">{N_skipped}</div><div class="lbl">pares descartados</div></div>
    </div>
  </header>

  <section>
    <h2>Integrações identificadas</h2>
    <div class="cards">
      <!-- Para cada par nos results: -->
      <div class="card">
        <div>
          <div class="card-title">{table_a} × {table_b}</div>
          <div class="card-key">{col_a} ↔ {col_b}</div>
          <div class="card-meta">Afinidade semântica: {affinity:.2f}</div>
          <div class="aff-bar-wrap">
            <div class="aff-bar"><div class="aff-fill" style="width:{affinity*100:.0f}%"></div></div>
            <span class="aff-num">{affinity:.2f}</span>
          </div>
          <a class="report-link" href="{report_path}">Ver relatório completo →</a>
        </div>
        <div>
          <span class="conf-pill conf-high">{confidence:.0%}</span>  <!-- conf-high/medium/low conforme valor -->
        </div>
      </div>
      <!-- repetir para cada integração -->
    </div>
  </section>

  <section>
    <h2>Pares descartados (afinidade &lt; {threshold})</h2>
    <table class="skip-table">
      <thead><tr><th>Tabela A</th><th>Tabela B</th><th>Afinidade</th><th>Motivo</th></tr></thead>
      <tbody>
        <!-- Para cada par em skipped: -->
        <tr>
          <td>{table_a}</td>
          <td>{table_b}</td>
          <td>{affinity:.2f}</td>
          <td>Sem grupos de domínio em comum e score semântico baixo</td>
        </tr>
      </tbody>
    </table>
  </section>

  <footer>Gerado pelo Sistema de Integração Semântica · {date}</footer>
</div>
</body>
</html>
```

Salve em: `output/reports/mapa_integracoes_{dir_stem}_{date}.html`

---

## Cuidados

- Use `nrows=0` para ler apenas os nomes das colunas na Etapa 1 — não carregue os dados completos antes de saber se o par é aprovado.
- Se um arquivo falhar ao carregar, pule-o e informe o usuário, sem interromper o mapeamento.
- O limiar padrão é 0.45. Se nenhum par for aprovado, reduza para 0.30 automaticamente antes de perguntar ao usuário.
- Links `href` nos cards do HTML devem ser caminhos relativos ao arquivo HTML gerado (use `../../` se necessário, ou paths absolutos).
- Normalize o `stem` dos arquivos: lowercase, substitua espaços e caracteres especiais por `_`.
