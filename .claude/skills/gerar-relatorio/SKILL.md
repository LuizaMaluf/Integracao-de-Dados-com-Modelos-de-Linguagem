---
name: gerar-relatorio
description: Gera um relatório executivo em HTML com CSS a partir dos resultados da Decision Layer (identificar-chave). Consolida a Integration Key identificada, ranking de candidatos, evidências, transformações necessárias, código de implementação e contexto de domínio em uma página HTML estilizada, salva em output/reports/. Use SEMPRE que o usuário quiser documentar uma decisão de integração, gerar um relatório de análise, registrar a Integration Key entre duas bases, ou compartilhar os resultados. Disparar quando o usuário disser "gera um relatório", "documenta isso", "quero um relatório do resultado", "manda o resultado formatado".
input:
  - type: json
    path: output/identificar_chave_{table_a}__{table_b}.json
    description: Resultado da Decision Layer (obrigatório)
  - type: json
    path: output/contexts/context_{domain}.json
    description: Domain Context usado na integração (opcional)
    optional: true
output:
  - type: html
    path: output/reports/relatorio_{table_a}__{table_b}_{date}.html
---

## Contexto do projeto

```
PROJECT_ROOT = /home/luiza-maluf/Área de trabalho/tcc/fase01
OUTPUT_REPORTS = PROJECT_ROOT/output/reports/
```

## Entrada esperada

O usuário pode fornecer:
1. **Caminho para JSON** produzido pela skill `identificar-chave` (ex: `output/identificar_chave_empenhos__pagamentos.json`)
2. **Dois arquivos CSV** — nesse caso, rode primeiro o pipeline de `identificar-chave` inline e então gere o relatório
3. **Resultado colado na conversa** — parse diretamente

Se nenhuma entrada for fornecida, liste os JSONs disponíveis em `output/` e pergunte qual usar.

---

## Como gerar

1. Leia o JSON de entrada e extraia: `summary`, `candidate_keys`, `best_match`
2. Preencha o template HTML abaixo com os dados reais — nunca deixe placeholders `{...}` vazios
3. Para a seção de metodologia, use `summary.analysis_steps` e `summary.heuristics` se existirem; caso contrário, use os valores padrão do sistema
4. Salve em: `output/reports/relatorio_{stem_a}__{stem_b}_{YYYY-MM-DD}.html`
5. Informe o caminho completo ao usuário

---

## Template HTML

Gere exatamente este HTML, substituindo todos os `{placeholders}` por dados reais:

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Relatório de Integração — {table_a} × {table_b}</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 15px;
      line-height: 1.6;
      color: #1a1a2e;
      background: #f4f6fb;
    }

    /* ── Layout ── */
    .page { max-width: 960px; margin: 0 auto; padding: 2rem 1.5rem 4rem; }

    /* ── Header ── */
    header {
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
      color: #fff;
      border-radius: 12px;
      padding: 2.5rem 2rem;
      margin-bottom: 2rem;
    }
    header h1 { font-size: 1.6rem; font-weight: 700; margin-bottom: 0.4rem; }
    header .subtitle { opacity: 0.75; font-size: 0.9rem; }
    .meta-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 0.75rem;
      margin-top: 1.5rem;
    }
    .meta-item { background: rgba(255,255,255,0.08); border-radius: 8px; padding: 0.6rem 0.9rem; }
    .meta-item .label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: .06em; opacity: 0.6; }
    .meta-item .value { font-size: 0.95rem; font-weight: 600; margin-top: 0.1rem; }

    /* ── Confidence badge ── */
    .confidence-hero {
      display: flex; align-items: center; gap: 1.5rem;
      background: #fff; border-radius: 12px; padding: 1.5rem 2rem;
      margin-bottom: 1.5rem;
      box-shadow: 0 1px 4px rgba(0,0,0,.08);
    }
    .conf-gauge {
      flex-shrink: 0;
      width: 80px; height: 80px;
      border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      font-size: 1.3rem; font-weight: 800;
      color: #fff;
    }
    .conf-high   { background: #22c55e; }
    .conf-medium { background: #f59e0b; }
    .conf-low    { background: #ef4444; }
    .conf-info h2 { font-size: 1.1rem; }
    .conf-info p  { color: #555; font-size: 0.9rem; margin-top: 0.25rem; }
    .key-tag {
      display: inline-block;
      background: #eef2ff; color: #4338ca;
      border-radius: 6px; padding: 0.2rem 0.6rem;
      font-family: monospace; font-size: 0.95rem;
      font-weight: 600;
    }

    /* ── Sections ── */
    section { background: #fff; border-radius: 12px; padding: 1.75rem 2rem; margin-bottom: 1.5rem; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
    section h2 { font-size: 1rem; font-weight: 700; color: #0f3460; margin-bottom: 1.25rem; padding-bottom: 0.5rem; border-bottom: 2px solid #eef2ff; }
    section h3 { font-size: 0.9rem; font-weight: 600; color: #374151; margin: 1.25rem 0 0.5rem; }

    /* ── Tables ── */
    .data-table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
    .data-table th {
      background: #f8faff; color: #374151;
      font-size: 0.75rem; text-transform: uppercase; letter-spacing: .05em;
      padding: 0.6rem 0.8rem; text-align: left; border-bottom: 2px solid #e5e7eb;
    }
    .data-table td { padding: 0.6rem 0.8rem; border-bottom: 1px solid #f3f4f6; vertical-align: top; }
    .data-table tr:last-child td { border-bottom: none; }
    .data-table tr:hover td { background: #fafbff; }

    /* ── Score bar ── */
    .score-wrap { display: flex; align-items: center; gap: 0.5rem; }
    .score-bar { flex: 1; height: 6px; background: #e5e7eb; border-radius: 3px; overflow: hidden; }
    .score-fill { height: 100%; border-radius: 3px; background: #4f46e5; }
    .score-num { font-size: 0.8rem; font-weight: 600; color: #374151; min-width: 36px; text-align: right; }

    /* ── Decision badges ── */
    .badge {
      display: inline-block; border-radius: 99px; padding: 0.15rem 0.6rem;
      font-size: 0.75rem; font-weight: 600;
    }
    .badge-best      { background: #dcfce7; color: #166534; }
    .badge-candidate { background: #fef9c3; color: #854d0e; }
    .badge-rejected  { background: #fee2e2; color: #991b1b; }

    /* ── Verdict ── */
    .verdict-compat  { color: #166534; font-weight: 700; }
    .verdict-partial { color: #854d0e; font-weight: 700; }
    .verdict-incompat{ color: #991b1b; font-weight: 700; }

    /* ── Evidence lists ── */
    .ev-list { list-style: none; display: flex; flex-direction: column; gap: 0.3rem; }
    .ev-list li { font-size: 0.88rem; padding-left: 1.4rem; position: relative; }
    .ev-list li::before { position: absolute; left: 0; }
    .ev-for  li::before { content: "✓"; color: #22c55e; font-weight: 700; }
    .ev-against li::before { content: "✗"; color: #ef4444; font-weight: 700; }
    .ev-transform li::before { content: "→"; color: #f59e0b; font-weight: 700; }

    /* ── Code blocks ── */
    pre {
      background: #1e1e2e; color: #cdd6f4;
      border-radius: 8px; padding: 1.25rem 1.5rem;
      font-size: 0.82rem; line-height: 1.55;
      overflow-x: auto; margin: 0.75rem 0;
    }
    code { font-family: 'Fira Code', 'Cascadia Code', 'Courier New', monospace; }
    .lang-label { font-size: 0.7rem; color: #6b7280; font-weight: 600; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: .05em; }

    /* ── Metrics grid ── */
    .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; }
    .metric-card { background: #f8faff; border-radius: 8px; padding: 1rem; text-align: center; }
    .metric-card .m-val { font-size: 1.5rem; font-weight: 800; color: #0f3460; }
    .metric-card .m-label { font-size: 0.75rem; color: #6b7280; margin-top: 0.2rem; }

    /* ── Warning banner ── */
    .warning-banner {
      background: #fffbeb; border: 1px solid #f59e0b; border-radius: 8px;
      padding: 0.75rem 1rem; font-size: 0.88rem; color: #92400e;
      margin-bottom: 1.5rem; display: flex; align-items: flex-start; gap: 0.5rem;
    }
    .warning-banner::before { content: "⚠️"; flex-shrink: 0; }

    /* ── Two-column info ── */
    .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
    .info-card { background: #f8faff; border-radius: 8px; padding: 1rem; }
    .info-card .label { font-size: 0.75rem; color: #6b7280; text-transform: uppercase; letter-spacing: .05em; }
    .info-card .value { font-size: 0.95rem; font-weight: 600; margin-top: 0.2rem; font-family: monospace; }

    /* ── Footer ── */
    footer { text-align: center; color: #9ca3af; font-size: 0.8rem; margin-top: 3rem; }

    @media (max-width: 600px) {
      .two-col { grid-template-columns: 1fr; }
      .confidence-hero { flex-direction: column; text-align: center; }
    }
  </style>
</head>
<body>
<div class="page">

  <!-- HEADER -->
  <header>
    <h1>Relatório de Integração de Dados</h1>
    <div class="subtitle">{table_a} × {table_b}</div>
    <div class="meta-grid">
      <div class="meta-item"><div class="label">Data</div><div class="value">{YYYY-MM-DD}</div></div>
      <div class="meta-item"><div class="label">Domínio</div><div class="value">{domain_name}</div></div>
      <div class="meta-item"><div class="label">Domain Context</div><div class="value">{context_path ou "defaults internos"}</div></div>
      <div class="meta-item"><div class="label">Cobertura de contexto</div><div class="value">{coverage:.0%}</div></div>
    </div>
  </header>

  <!-- AVISO DE CONFIANÇA BAIXA (incluir só se confidence < 0.6) -->
  <!-- <div class="warning-banner">Confiança abaixo do limiar recomendado (0.6) — revisar manualmente antes de usar em produção.</div> -->

  <!-- HERO: INTEGRATION KEY -->
  <div class="confidence-hero">
    <div class="conf-gauge conf-high">{confidence_pct}%</div>  <!-- conf-high / conf-medium / conf-low conforme valor -->
    <div class="conf-info">
      <h2>Integration Key identificada</h2>
      <p>
        <span class="key-tag">{table_a}.{col_a}</span>
        &nbsp;↔&nbsp;
        <span class="key-tag">{table_b}.{col_b}</span>
      </p>
      <p>{justification}</p>
    </div>
  </div>

  <!-- SEÇÃO 1: RESUMO EXECUTIVO -->
  <section>
    <h2>1. Resumo Executivo</h2>
    <p>{1–2 parágrafos: quais tabelas foram analisadas, qual Integration Key foi identificada, grau de confiança e recomendação de ação imediata}</p>
  </section>

  <!-- SEÇÃO 2: TABELAS ANALISADAS -->
  <section>
    <h2>2. Tabelas Analisadas</h2>
    <div class="two-col">
      <div class="info-card">
        <div class="label">Tabela A</div>
        <div class="value">{table_a}</div>
        <div style="margin-top:.5rem;font-size:.85rem;color:#374151">{rows_a} linhas · {cols_a} colunas</div>
      </div>
      <div class="info-card">
        <div class="label">Tabela B</div>
        <div class="value">{table_b}</div>
        <div style="margin-top:.5rem;font-size:.85rem;color:#374151">{rows_b} linhas · {cols_b} colunas</div>
      </div>
    </div>
  </section>

  <!-- SEÇÃO 3: METODOLOGIA -->
  <section>
    <h2>3. Metodologia</h2>
    <h3>Dimensões de análise</h3>
    <table class="data-table">
      <thead><tr><th>Dimensão</th><th>Peso</th><th>O que mede</th></tr></thead>
      <tbody>
        <tr><td>Semântica</td><td>35%</td><td>Similaridade de nomes de colunas e grupos do Domain Context</td></tr>
        <tr><td>Match rate</td><td>30%</td><td>Taxa de correspondência de valores após normalização</td></tr>
        <tr><td>Estrutural</td><td>20%</td><td>Compatibilidade de tipos, cardinalidade e taxa de nulos</td></tr>
        <tr><td>Padrão</td><td>15%</td><td>Conformidade com padrões regex do domínio</td></tr>
      </tbody>
    </table>
    <h3>Parâmetros aplicados</h3>
    <table class="data-table">
      <thead><tr><th>Parâmetro</th><th>Valor</th></tr></thead>
      <tbody>
        <tr><td>Limiar semântico mínimo para candidato</td><td>≥ 0.30</td></tr>
        <tr><td>Limiar de confiança recomendado</td><td>≥ 0.60</td></tr>
        <tr><td>Normalização de valores</td><td>strip + upper + remover pontuação</td></tr>
        <tr><td>Candidato a PK: unicidade mínima</td><td>≥ 95%</td></tr>
        <tr><td>Candidato a PK: taxa de nulos máxima</td><td>≤ 2%</td></tr>
      </tbody>
    </table>
  </section>

  <!-- SEÇÃO 4: CANDIDATOS -->
  <section>
    <h2>4. Candidatos Analisados</h2>
    <table class="data-table">
      <thead>
        <tr>
          <th>#</th><th>Coluna A</th><th>Coluna B</th>
          <th>Score</th><th>Match Rate</th><th>Cardinalidade</th><th>Decisão</th>
        </tr>
      </thead>
      <tbody>
        <!-- Para cada candidate_key, gere uma linha: -->
        <tr>
          <td>1</td>
          <td><code>{col_a}</code></td>
          <td><code>{col_b}</code></td>
          <td>
            <div class="score-wrap">
              <div class="score-bar"><div class="score-fill" style="width:{score*100}%"></div></div>
              <span class="score-num">{score:.2f}</span>
            </div>
          </td>
          <td>{match_rate:.1%}</td>
          <td>{cardinality}</td>
          <td><span class="badge badge-best">Melhor</span></td>   <!-- badge-best / badge-candidate / badge-rejected -->
        </tr>
        <!-- repita para cada candidato -->
      </tbody>
    </table>
  </section>

  <!-- SEÇÃO 5: CHAVE RECOMENDADA -->
  <section>
    <h2>5. Integration Key Recomendada</h2>
    <div class="two-col" style="margin-bottom:1.25rem">
      <div class="info-card">
        <div class="label">Tabela A → coluna</div>
        <div class="value">{col_a}</div>
      </div>
      <div class="info-card">
        <div class="label">Tabela B → coluna</div>
        <div class="value">{col_b}</div>
      </div>
    </div>

    <h3>Evidências favoráveis</h3>
    <ul class="ev-list ev-for">
      <!-- Para cada evidence_for: -->
      <li>{evidence}</li>
    </ul>

    <!-- Incluir só se houver evidence_against -->
    <h3>Limitações identificadas</h3>
    <ul class="ev-list ev-against">
      <li>{evidence_against}</li>
    </ul>

    <!-- Incluir só se houver required_transformations -->
    <h3>Transformações necessárias</h3>
    <ul class="ev-list ev-transform">
      <li>{transformation}</li>
    </ul>
  </section>

  <!-- SEÇÃO 6: IMPLEMENTAÇÃO -->
  <section>
    <h2>6. Implementação</h2>
    <h3>Python (pandas)</h3>
    <div class="lang-label">Python</div>
    <pre><code>import pandas as pd

df_a = pd.read_csv('{arquivo_a}', sep=';', encoding='utf-8', dtype=str)
df_b = pd.read_csv('{arquivo_b}', sep=';', encoding='utf-8', dtype=str)

# {transformações necessárias, se houver}

resultado = df_a.merge(
    df_b,
    left_on='{col_a}',
    right_on='{col_b}',
    how='inner'
)
print(f"Resultado: {len(resultado)} linhas")</code></pre>

    <h3>SQL</h3>
    <div class="lang-label">SQL</div>
    <pre><code>SELECT a.*, b.{colunas_relevantes_b}
FROM {tabela_a} a
INNER JOIN {tabela_b} b
    ON a.{col_a} = b.{col_b};</code></pre>
  </section>

  <!-- SEÇÃO 7: QUALIDADE DO JOIN -->
  <section>
    <h2>7. Qualidade do Join</h2>
    <div class="metrics-grid">
      <div class="metric-card"><div class="m-val">{match_a_in_b:.0%}</div><div class="m-label">Match rate A → B</div></div>
      <div class="metric-card"><div class="m-val">{match_b_in_a:.0%}</div><div class="m-label">Match rate B → A</div></div>
      <div class="metric-card"><div class="m-val">~{estimated_inner}</div><div class="m-label">Linhas no INNER JOIN</div></div>
      <div class="metric-card"><div class="m-val">~{orphans_a}</div><div class="m-label">Linhas de A sem match</div></div>
    </div>
  </section>

  <!-- SEÇÃO 8: PRÓXIMOS PASSOS -->
  <section>
    <h2>8. Próximos Passos</h2>
    <ol style="padding-left:1.25rem;display:flex;flex-direction:column;gap:.4rem;font-size:.9rem">
      <li>Validar o join em amostra pequena antes de executar em produção</li>
      <!-- Se houver transformações: -->
      <li>{transformação específica necessária}</li>
      <li>Monitorar linhas órfãs periodicamente — divergências podem indicar atraso de carga entre sistemas</li>
    </ol>
  </section>

  <!-- APÊNDICE: TODOS OS CANDIDATOS -->
  <section>
    <h2>Apêndice — Todos os Candidatos Avaliados</h2>
    <table class="data-table">
      <thead>
        <tr>
          <th>Coluna A</th><th>Coluna B</th><th>Score</th>
          <th>Match A→B</th><th>Veredito</th><th>Principal evidência</th>
        </tr>
      </thead>
      <tbody>
        <!-- Para TODOS os candidate_keys, incluindo rejeitados: -->
        <tr>
          <td><code>{col_a}</code></td>
          <td><code>{col_b}</code></td>
          <td>{score:.2f}</td>
          <td>{match_rate:.1%}</td>
          <td><span class="verdict-compat">{verdict}</span></td>  <!-- verdict-compat / verdict-partial / verdict-incompat -->
          <td style="font-size:.82rem;color:#555">{evidence_for[0] ou evidence_against[0]}</td>
        </tr>
      </tbody>
    </table>
  </section>

  <footer>
    Gerado pelo Sistema de Integração Semântica · {YYYY-MM-DD}
  </footer>

</div>
</body>
</html>
```

---

## Cuidados

- **Nunca deixe `{placeholders}` no HTML final** — preencha com dados reais ou remova o elemento
- Se `confidence < 0.6`: remova o comentário do `warning-banner` e use `conf-low` no gauge
- Se `confidence` entre 0.6–0.8: use `conf-medium`; acima de 0.8: use `conf-high`
- Para cada `candidate_key`: use `badge-best` para o melhor, `badge-candidate` para os demais, `badge-rejected` para os com score < 0.3
- Para `verdict` na coluna do apêndice: `verdict-compat` (COMPATÍVEL), `verdict-partial` (PARCIALMENTE), `verdict-incompat` (INCOMPATÍVEL)
- Se não houver `evidence_against` ou `required_transformations`, remova as subseções correspondentes da Seção 5
- Se for Derived Key (chave composta ou reconstruída), adapte a Seção 6 para mostrar a fórmula de reconstrução
- `estimated_inner` = `rows_a × match_rate_a_in_b` (estimativa)
- `orphans_a` = `rows_a × (1 - match_rate_a_in_b)`
