# Relatório de Integração: Convênios x Transferências

**Data:** 2026-05-21
**Arquivo de entrada:** `output/identificar_chave_convenios__transferencias.json`

---

## 1. Visão Geral das Tabelas

| Atributo | Convênios (`convenios.csv`) | Transferências (`transferencias.csv`) |
|---|---|---|
| Linhas | 300 | 450 |
| Colunas | 8 | 6 |

---

## 2. Metodologia de Análise

A identificação da chave de integração seguiu 8 etapas:

1. Carregamento e perfilamento das tabelas (dtype, unicidade, nulos, comprimento médio, top-5 valores).
2. Detecção de grupo de domínio por similaridade semântica.
3. Detecção de padrão estrutural por regex (convênio: `dddddd/YYYY`, CNPJ, CPF, etc.).
4. Geração de pares candidatos: produto cartesiano A x B, filtrado por score semântico >= 0.30.
5. Pontuação composta: `0.35 x semântico + 0.30 x match_rate + 0.20 x estrutural + 0.15 x padrão`.
6. Normalização: strip + upper + remoção de pontuação.
7. Ranking e seleção do `best_match`.
8. Validação por LLM (claude-sonnet-4-6).

---

## 3. Candidatos Identificados

### Candidato 1 — Chave Composta por Número e Ano do Convênio (Melhor Match)

| Métrica | Valor |
|---|---|
| Colunas em A | `nr_convenio`, `ano_convenio` |
| Colunas em B | `numero_convenio`, `exercicio` |
| Score semântico | 0.75 |
| Score estrutural | 0.70 |
| Match rate A→B | 55% |
| Match rate B→A | 38% |
| Score de padrão | 0.80 |
| Score composto | 0.618 |
| Padrão detectado | `dddddd/YYYY` (ambos) |

Evidências favoráveis: mesmo domínio (`convenio`), mesmo padrão estrutural, nomes com radical compartilhado.

Evidências contrárias: match rate moderado (55%/38%), necessidade de chave composta.

Transformações necessárias: normalizar separador (`'/'` → `'-'`), remover zeros à esquerda se necessário.

---

### Candidato 2 — CNPJ do Convenente x CNPJ do Beneficiário

| Métrica | Valor |
|---|---|
| Colunas em A | `cnpj_convenente` |
| Colunas em B | `cnpj_beneficiario` |
| Score semântico | 0.65 |
| Score estrutural | 0.90 |
| Match rate A→B | 30% |
| Match rate B→A | 20% |
| Score de padrão | 0.95 |
| Score composto | 0.548 |

Evidências contrárias: match rate baixo (30%/20%), convenente e beneficiário são entidades distintas.

---

## 4. Melhor Correspondência Selecionada

**Confiança: 0.58** (abaixo do limiar de alerta de 0.60 — validação manual recomendada)

Chave: `nr_convenio + ano_convenio` (convenios) ↔ `numero_convenio + exercicio` (transferências)

Justificativa LLM: "A chave composta é a melhor opção disponível, mas com confiança abaixo do ideal (0.58). Match rate moderado sugere divergências entre as bases. Recomenda-se validação manual antes de usar em produção."

---

## 5. Análise de Risco

| Fator | Avaliação |
|---|---|
| Confiança abaixo do limiar | Alta — 0.58 < 0.60 |
| Match rate assimétrico | Média — 55% vs 38% |
| Chave composta obrigatória | Média |
| Divergências de formatação | Baixa — transformações documentadas |
| Perda de registros no join | Alta — 62% dos registros de transferências podem não ter par |

---

## 6. Recomendações

1. Validação manual obrigatória antes de usar em produção.
2. Investigar divergências de cadastro entre os sistemas de origem.
3. Tratar sempre a chave como composta (número + ano).
4. Aplicar as transformações de normalização antes do join.
5. Não usar CNPJ como chave de integração — match rate insuficiente.
6. Monitorar qualidade dos registros após a integração.

---

## 7. Resumo Executivo

A análise identificou dois pares candidatos. O melhor é a chave composta `nr_convenio + ano_convenio` (convenios) com `numero_convenio + exercicio` (transferências), com score composto de 0.618 e confiança final de 0.58. A confiança está abaixo do limiar de alerta (0.60), indicando que a integração não é segura para uso automático em produção sem validação manual prévia. O match rate assimétrico (55% vs 38%) aponta para divergências de cadastro entre os dois sistemas.
