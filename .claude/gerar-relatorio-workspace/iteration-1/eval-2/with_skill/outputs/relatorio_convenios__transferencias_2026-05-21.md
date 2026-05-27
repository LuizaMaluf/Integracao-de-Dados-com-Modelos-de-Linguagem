# Relatório de Integração de Dados
**Data:** 2026-05-21  
**Analista:** Sistema de Integração Semântica  
**Domínio:** Execução Orçamentária e Transferências Governamentais Federais

---

## 1. Resumo Executivo

Este relatório documenta a análise de integração entre as tabelas **convenios** (300 linhas, 8 colunas) e **transferencias** (450 linhas, 6 colunas). A análise identificou como melhor chave de integração o par composto `nr_convenio + ano_convenio` (tabela convenios) ↔ `numero_convenio + exercicio` (tabela transferencias), com score composto de 0.618 e confiança de 0.58.

> ⚠️ **Confiança abaixo do limiar recomendado (0.58 < 0.60) — revisar manualmente antes de usar em produção.** O match rate moderado (55% A→B / 38% B→A) indica possíveis divergências de cadastro entre os sistemas. Recomenda-se validar o join em amostra antes de executar sobre a base completa e aplicar as transformações de normalização descritas na seção 5.

---

## 2. Tabelas Analisadas

|  | Tabela A | Tabela B |
|---|---|---|
| **Nome** | convenios | transferencias |
| **Arquivo** | convenios.csv | transferencias.csv |
| **Linhas** | 300 | 450 |
| **Colunas** | 8 | 6 |

---

## 3. Metodologia e Processo de Identificação

### 3.1 Dimensões de análise

A análise combinou três dimensões, ponderadas em score composto:

| Dimensão | Peso | O que mede |
|----------|------|------------|
| Semântica | 35% | Similaridade entre nomes de colunas e grupos de domínio orçamentário |
| Match rate | 30% | Taxa de correspondência de valores após normalização |
| Estrutural | 20% | Compatibilidade de tipos, cardinalidade e taxa de nulos |
| Padrão | 15% | Conformidade com padrões regex do domínio (NE, convênio, CNPJ, CPF, código_5dig) |

### 3.2 Passos da análise

1. Carregamento e perfilamento de ambas as tabelas (dtype, unicidade, nulos, comprimento médio, top-5 valores)
2. Detecção de grupo de domínio por similaridade semântica com aliases do dicionário DOMAIN_SEMANTIC_GROUPS
3. Detecção de padrão estrutural por regex (NE: YYYYNEnnnnnn, convênio: dddddd/YYYY, CNPJ, CPF, código_5dig)
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
- grupos de domínio incompatíveis
- score semântico < 0.15

---

## 4. Candidatos Analisados

| Rank | Coluna A | Coluna B | Score | Match Rate (A→B) | Match Rate (B→A) | Decisão |
|------|----------|----------|-------|-----------------|-----------------|---------|
| #1 | `nr_convenio` + `ano_convenio` | `numero_convenio` + `exercicio` | 0.618 | 55% | 38% | ✅ Melhor |
| #2 | `cnpj_convenente` | `cnpj_beneficiario` | 0.548 | 30% | 20% | 🔶 Candidato |

---

## 5. Chave de Integração Recomendada

**Tabela A:** `convenios` → colunas: `nr_convenio`, `ano_convenio`  
**Tabela B:** `transferencias` → colunas: `numero_convenio`, `exercicio`  
**Confiança:** 0.58 / 1.0

> ⚠️ Confiança abaixo do limiar recomendado — revisar manualmente antes de usar em produção.

### Evidências favoráveis

- Mesmo grupo de domínio: convenio
- Mesmo padrão estrutural: dddddd/YYYY
- Score semântico bom: nomes compartilham radical

### Limitações identificadas

- Match rate moderado (55%/38%): possíveis divergências de cadastro entre sistemas
- Chave composta necessária: ano deve ser usado junto com número do convênio

### Transformações necessárias

1. **Normalizar separador:** substituir `'/'` por `'-'` antes do join  
   Exemplo: `'123456/2023'` → `'123456-2023'` (aplicar em `nr_convenio`/`ano_convenio` e em `numero_convenio`/`exercicio`)
2. **Remover zeros à esquerda:** no número do convênio se presentes em apenas uma das bases  
   Exemplo: `'007890/2022'` → `'7890/2022'` (verificar qual base usa zero-padding)

---

## 6. Implementação

### Python (pandas)

```python
import pandas as pd

# Carregar tabelas
df_a = pd.read_csv('convenios.csv', sep=';', encoding='utf-8', dtype=str)
df_b = pd.read_csv('transferencias.csv', sep=';', encoding='utf-8', dtype=str)

# Transformação 1: criar chave composta normalizada (substituir '/' por '-')
df_a['_chave_join'] = (
    df_a['nr_convenio'].str.strip().str.upper().str.replace('/', '-', regex=False)
    + '_'
    + df_a['ano_convenio'].str.strip()
)

df_b['_chave_join'] = (
    df_b['numero_convenio'].str.strip().str.upper().str.replace('/', '-', regex=False)
    + '_'
    + df_b['exercicio'].str.strip()
)

# Transformação 2: remover zeros à esquerda no número (se necessário)
# df_a['_chave_join'] = df_a['_chave_join'].str.lstrip('0')
# df_b['_chave_join'] = df_b['_chave_join'].str.lstrip('0')

# Join pela chave composta normalizada
resultado = df_a.merge(
    df_b,
    on='_chave_join',
    how='inner'  # ou 'left' se quiser preservar registros sem match
)

print(f"Resultado: {len(resultado)} linhas")
print(f"Sem correspondência em A: {len(df_a) - len(resultado.drop_duplicates('_chave_join'))} registros")
```

### SQL

```sql
SELECT
    a.*,
    b.numero_convenio,
    b.exercicio,
    b.valor_transferencia  -- ajuste conforme colunas reais de transferencias
FROM convenios a
INNER JOIN transferencias b
    ON REPLACE(a.nr_convenio, '/', '-') = REPLACE(b.numero_convenio, '/', '-')
    AND a.ano_convenio = b.exercicio
-- WHERE a.ano_convenio = '2023'  -- filtro opcional por exercício
;
```

---

## 7. Qualidade do Join

| Métrica | Valor |
|---------|-------|
| Match rate A → B | 55% |
| Match rate B → A | 38% |
| Registros estimados no resultado (INNER) | ~165 (55% × 300) |
| Registros A sem correspondência | ~135 |
| Registros B sem correspondência | ~279 |

---

## 8. Próximos Passos Recomendados

1. Validar o join em amostra pequena (ex: 20 registros) antes de executar em produção
2. Aplicar normalização do separador (`'/'` → `'-'`) em ambas as bases antes do join
3. Verificar e padronizar zeros à esquerda no campo número do convênio entre as duas bases
4. Investigar os ~45% de registros de convenios sem correspondência em transferencias: podem indicar convênios ainda não executados ou divergência de cadastro
5. Monitorar linhas órfãs periodicamente — variações inesperadas podem indicar divergência entre as bases ao longo do tempo

---

## Apêndice: Todos os Candidatos Avaliados

| Rank | Colunas A | Colunas B | Score Semântico | Score Estrutural | Score Padrão | Score Composto | Match Rate A→B | Match Rate B→A | Grupo A | Grupo B | Padrão A | Padrão B |
|------|-----------|-----------|----------------|-----------------|-------------|---------------|---------------|---------------|---------|---------|---------|---------|
| #1 | `nr_convenio`, `ano_convenio` | `numero_convenio`, `exercicio` | 0.75 | 0.70 | 0.80 | 0.618 | 55% | 38% | convenio | convenio | dddddd/YYYY | dddddd/YYYY |
| #2 | `cnpj_convenente` | `cnpj_beneficiario` | 0.65 | 0.90 | 0.95 | 0.548 | 30% | 20% | cnpj | cnpj | CNPJ | CNPJ |
