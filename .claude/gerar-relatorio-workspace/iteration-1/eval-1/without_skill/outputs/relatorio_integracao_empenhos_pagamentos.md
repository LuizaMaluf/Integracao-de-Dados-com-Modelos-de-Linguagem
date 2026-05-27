# Relatório de Análise de Integração Semântica
## Tabelas: `empenhos_a` x `pagamentos_b`

**Data de geração:** 2026-05-21
**Arquivo de entrada:** `output/identificar_chave_empenhos_a__pagamentos_b.json`

---

## 1. Visão Geral

Este relatório documenta o processo de identificação automática da melhor chave de integração entre duas tabelas do governo federal brasileiro: **empenhos_a** e **pagamentos_b**. A análise combina heurísticas estruturais, similaridade semântica e validação por modelo de linguagem (LLM) para determinar como as tabelas devem ser unidas.

---

## 2. Caracterização das Tabelas

| Atributo | empenhos_a | pagamentos_b |
|---|---|---|
| Arquivo fonte | empenhos_a.csv | pagamentos_b.csv |
| Linhas | 150 | 120 |
| Colunas | 3 | 3 |

---

## 3. Resultado — Melhor Chave de Integração

| Atributo | Valor |
|---|---|
| Coluna em empenhos_a | `nr_empenho` |
| Coluna em pagamentos_b | `numero_empenho` |
| Confiança | **0.97** (muito alta) |
| Score composto | 0.912 |
| Match rate A→B | 80% |
| Match rate B→A | 100% |
| Transformações | Nenhuma |

**Justificativa (validação LLM):** *"nr_empenho ↔ numero_empenho é a única chave viável. Ambas seguem padrão YYYYNEnnnnnn. Match 100% (B→A), 80% (A→B). Assimetria esperada: pagamentos_b representa apenas empenhos pagos. Use LEFT JOIN de empenhos_a em pagamentos_b sem transformações."*

---

## 4. Recomendação de JOIN

```sql
SELECT e.*, p.*
FROM empenhos_a e
LEFT JOIN pagamentos_b p
    ON e.nr_empenho = p.numero_empenho;
```
