# Relatório de Integração de Dados
**Data:** 2026-05-21  
**Analista:** Sistema de Integração Semântica  
**Domínio:** Execução Orçamentária e Transferências Governamentais Federais

---

## 1. Resumo Executivo

A análise de integração foi conduzida entre as tabelas **empenhos_a** (150 linhas, 3 colunas) e **pagamentos_b** (120 linhas, 3 colunas), pertencentes ao domínio de Execução Orçamentária Federal. O sistema identificou, com grau de confiança de **0.97/1.0**, que a chave de integração entre as duas bases é o par de colunas `nr_empenho` (empenhos_a) ↔ `numero_empenho` (pagamentos_b). Ambas as colunas seguem o padrão de Nota de Empenho (YYYYNEnnnnnn), apresentam alta cardinalidade, ausência de nulos e match rate de 100% no sentido B→A — indicando que todos os pagamentos registrados possuem empenho correspondente.

A assimetria observada no sentido A→B (80%) é esperada e semanticamente consistente: a tabela `pagamentos_b` representa apenas os empenhos que foram efetivamente pagos, sendo um subconjunto natural de `empenhos_a`. **Recomendação de ação imediata:** utilizar LEFT JOIN de `empenhos_a` em `pagamentos_b` pela chave identificada, sem necessidade de transformações adicionais.

---

## 2. Tabelas Analisadas

| | Tabela A | Tabela B |
|---|---|---|
| **Nome** | empenhos_a | pagamentos_b |
| **Arquivo** | empenhos_a.csv | pagamentos_b.csv |
| **Linhas** | 150 | 120 |
| **Colunas** | 3 | 3 |

---

## 3. Metodologia e Processo de Identificação

### 3.1 Dimensões de análise

A análise combinou quatro dimensões, ponderadas em score composto:

| Dimensão | Peso | O que mede |
|----------|------|------------|
| Semântica | 35% | Similaridade entre nomes de colunas e grupos de domínio orçamentário |
| Match rate | 30% | Taxa de correspondência de valores após normalização |
| Estrutural | 20% | Compatibilidade de tipos, cardinalidade e taxa de nulos |
| Padrão | 15% | Conformidade com padrões regex do domínio (NE, convênio, CNPJ, etc.) |

### 3.2 Passos da análise

1. Carregamento e perfilamento de ambas as tabelas (dtype, unicidade, nulos, comprimento médio, top-5 valores)
2. Detecção de grupo de domínio por similaridade semântica com aliases do dicionário DOMAIN_SEMANTIC_GROUPS
3. Detecção de padrão estrutural por regex (NE: YYYYNEnnnnnn, convênio, CNPJ, CPF, código_5dig)
4. Geração de pares candidatos: produto cartesiano de colunas A × B, filtrado por score semântico ≥ 0.30
5. Pontuação composta: 0.35×semântico + 0.30×match_rate + 0.20×estrutural + 0.15×padrão
6. Normalização de valores: strip + upper + remoção de pontuação antes de calcular match rate
7. Ranking dos candidatos e seleção do best_match por maior score composto
8. Raciocínio LLM (claude-sonnet-4-6) para validação final e geração de justificativa em linguagem natural

### 3.3 Heurísticas aplicadas

| Parâmetro | Valor |
|-----------|-------|
| Limiar semântico mínimo para candidato | ≥ 0.30 |
| Limiar de confiança recomendado | ≥ 0.60 |
| Normalização de valores | strip + upper + remover pontuação |
| Candidato a PK: unicidade mínima | ≥ 95% |
| Candidato a PK: taxa de nulos máxima | ≤ 2% |

**Critérios de rejeição:**
- match_rate < 0.05 em ambas as direções
- grupos de domínio incompatíveis (ex: orgao vs programa)
- score semântico < 0.15

---

## 4. Candidatos Analisados

| Rank | Coluna A | Coluna B | Score | Match Rate A→B | Match Rate B→A | Cardinalidade | Decisão |
|------|----------|----------|-------|---------------|---------------|---------------|---------|
| #1 | nr_empenho | numero_empenho | 0.912 | 80% | 100% | Alta / Alta | ✅ Melhor |
| #2 | cd_orgao | cd_orgao_pagamento | 0.691 | 60% | 55% | Baixa (5 val.) | 🔶 Candidato auxiliar |
| #3 | nr_empenho | cd_orgao_pagamento | 0.098 | 0% | 0% | Alta / Baixa | ❌ Rejeitado |

---

## 5. Chave de Integração Recomendada

**Tabela A:** `empenhos_a` → coluna: `nr_empenho`  
**Tabela B:** `pagamentos_b` → coluna: `numero_empenho`  
**Confiança:** 0.97 / 1.0

### Evidências favoráveis

- Ambas seguem padrão YYYYNEnnnnnn (Nota de Empenho)
- Match rate B→A = 100%: todos os 120 pagamentos existem nos empenhos
- Match rate A→B = 80%: pagamentos_b é subconjunto de empenhos (esperado)
- Score semântico alto: 'nr_empenho' e 'numero_empenho' compartilham radical
- Mesmo grupo de domínio: nota_empenho
- Alta cardinalidade, zero nulos em ambas

### Limitações identificadas

Nenhuma evidência contrária identificada. A assimetria A→B (80%) é estruturalmente esperada, pois `pagamentos_b` representa apenas empenhos efetivamente pagos — não constitui uma limitação do join, mas sim uma característica do domínio.

---

## 6. Implementação

### Python (pandas)

```python
import pandas as pd

# Carregar tabelas
df_a = pd.read_csv('empenhos_a.csv', sep=';', encoding='utf-8', dtype=str)
df_b = pd.read_csv('pagamentos_b.csv', sep=';', encoding='utf-8', dtype=str)

# Join pela chave de empenho (sem transformações necessárias)
resultado = df_a.merge(
    df_b,
    left_on='nr_empenho',
    right_on='numero_empenho',
    how='left'  # LEFT JOIN preserva empenhos sem pagamento correspondente
)

print(f"Resultado: {len(resultado)} linhas")
print(f"Empenhos com pagamento: {resultado['numero_empenho'].notna().sum()}")
print(f"Empenhos sem pagamento: {resultado['numero_empenho'].isna().sum()}")
```

### SQL

```sql
SELECT
    a.*,
    b.numero_empenho AS b_numero_empenho
FROM empenhos_a a
LEFT JOIN pagamentos_b b
    ON a.nr_empenho = b.numero_empenho
-- Usar INNER JOIN se quiser apenas empenhos que possuem pagamento registrado
;
```

---

## 7. Qualidade do Join

| Métrica | Valor |
|---------|-------|
| Match rate A → B | 80% |
| Match rate B → A | 100% |
| Registros estimados no resultado (INNER JOIN) | ~120 |
| Registros A sem correspondência (LEFT JOIN) | ~30 |
| Registros B sem correspondência | 0 |

---

## 8. Próximos Passos Recomendados

1. Validar o join em amostra pequena antes de executar em produção
2. Decidir entre LEFT JOIN (preserva todos os empenhos, incluindo os sem pagamento) ou INNER JOIN (apenas empenhos pagos) conforme o objetivo da análise
3. Monitorar as ~30 linhas de empenhos sem correspondência periodicamente — podem indicar empenhos pendentes de pagamento ou divergência futura entre bases
4. Avaliar se a coluna `cd_orgao` / `cd_orgao_pagamento` pode ser usada como chave auxiliar de validação ou filtro de consistência

---

## Apêndice: Todos os Candidatos Avaliados

| Coluna A | Coluna B | Score Composto | Semântico | Estrutural | Match A→B | Match B→A | Padrão | Grupo A | Grupo B | Padrão A | Padrão B | Decisão |
|----------|----------|---------------|-----------|------------|-----------|-----------|--------|---------|---------|----------|----------|---------|
| nr_empenho | numero_empenho | 0.912 | 0.88 | 0.95 | 80% | 100% | 1.00 | nota_empenho | nota_empenho | YYYYNEnnnnnn | YYYYNEnnnnnn | ✅ Best match (confiança: 0.97) |
| cd_orgao | cd_orgao_pagamento | 0.691 | 0.72 | 0.80 | 60% | 55% | 0.85 | orgao | orgao | codigo_5dig | codigo_5dig | 🔶 Candidato — baixa cardinalidade, match insuficiente para chave primária |
| nr_empenho | cd_orgao_pagamento | 0.098 | 0.12 | 0.20 | 0% | 0% | 0.10 | nota_empenho | orgao | YYYYNEnnnnnn | codigo_5dig | ❌ Rejeitado — domínios incompatíveis, match 0% |
