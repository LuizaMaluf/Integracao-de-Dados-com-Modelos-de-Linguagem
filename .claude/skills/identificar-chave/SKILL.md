---
name: identificar-chave
description: Decision Layer do Integration Pipeline — recebe as evidências coletadas pelo comparar-colunas e decide a melhor Integration Key usando raciocínio LLM. Quando acionado diretamente pelo usuário (sem pipeline), também executa a coleta de evidências internamente. Quando nenhuma chave direta é encontrada (match < 50%), aciona busca de Derived Key via reconstrução de identificadores SIAFI. Use SEMPRE que o usuário quiser cruzar duas bases de dados, descobrir como fazer um join, encontrar a coluna comum entre duas fontes, ou identificar a Integration Key. Disparar quando o usuário disser "como faço pra cruzar essas duas tabelas?", "qual campo liga uma base na outra?", "quero integrar esses dois arquivos", "que coluna uso pra fazer o join?".
input:
  - type: json
    path: output/comparar_colunas_{table_a}__{table_b}.json
    description: Evidências da Evidence Layer (modo pipeline)
    optional: true
  - type: csv
    path: "{table_a}"
    description: Tabela A — usado quando acionado diretamente (sem pipeline)
    optional: true
  - type: csv
    path: "{table_b}"
    description: Tabela B — usado quando acionado diretamente (sem pipeline)
    optional: true
output:
  - type: json
    path: output/identificar_chave_{table_a}__{table_b}.json
---

## Contexto do projeto

```
PROJECT_ROOT = /home/luiza-maluf/Área de trabalho/tcc/fase01
```

Módulos disponíveis:
```python
import sys
sys.path.insert(0, "/home/luiza-maluf/Área de trabalho/tcc/fase01")

from src.loaders.csv_loader import CsvLoader
from src.agent.orchestrator import IntegrationAgent
from src.output.formatter import print_result
```

JSON de saída: `output/identificar_chave_{stem_a}__{stem_b}.json`

---

## Modo de operação

**Modo pipeline (Decision Layer):** acionado pelo `integrar-bases`. Recebe o JSON do `comparar-colunas` com todos os pares já avaliados. Não regenera candidatos — usa as evidências existentes para decidir a melhor Integration Key.

**Modo direto:** acionado pelo usuário sem passar pelo pipeline. Executa internamente o pipeline completo (carrega CSVs, gera candidatos, compara, decide).

---

## MODO PIPELINE — Decision Layer

### 1. Carregar evidências

```python
import json
from pathlib import Path

evidence = json.loads(Path("output/comparar_colunas_{stem_a}__{stem_b}.json").read_text())
candidates = evidence["pairs"]  # lista de pares já avaliados com match_rate, evidências etc.
```

### 2. Acionar LLM para decisão

Passe os candidatos diretamente para `reason_with_llm` — sem reprocessar CSVs.

```python
from src.agent.llm_reasoner import reason_with_llm
from src.loaders.base import TableMetadata

# Reconstruir TableMetadata a partir das evidências (sem reler os CSVs)
meta_a = TableMetadata(name=evidence["table_a"], columns=[p["col_a"] for p in candidates], dtypes={})
meta_b = TableMetadata(name=evidence["table_b"], columns=[p["col_b"] for p in candidates], dtypes={})

# Converter pares para CandidateKey
from src.agent.candidate_generator import CandidateKey
ck_list = [
    CandidateKey(
        columns_a=[p["col_a"]],
        columns_b=[p["col_b"]],
        match_rate=p["match_rate_normalized"]["a_in_b"],
        evidence_for=p["evidence_for"],
        evidence_against=p["evidence_against"],
        required_transformations=p["required_transformations"],
    )
    for p in candidates
]

result = reason_with_llm(meta_a, meta_b, ck_list)
```

### 3. Salvar resultado

Salve em `output/identificar_chave_{stem_a}__{stem_b}.json`.

---

## Entrada esperada (modo direto)

O usuário fornece dois arquivos CSV — em `$ARGUMENTS`, na mensagem, ou como contexto da conversa.

```
<arquivo_a.csv>  <arquivo_b.csv>
```

Parâmetros opcionais que o usuário pode mencionar:
- `--no-llm` ou "só heurísticas" — pular etapa de raciocínio com LLM
- `--sep` ou "separador vírgula" — alterar separador do CSV
- `--encoding` ou "arquivo em latin-1" — alterar encoding

---

## Pipeline de execução

### Opção 1 — Via módulos do projeto (preferencial)

```python
import sys, json
sys.path.insert(0, "/home/luiza-maluf/Área de trabalho/tcc/fase01")

from src.loaders.csv_loader import CsvLoader
from src.agent.orchestrator import IntegrationAgent
from src.output.formatter import print_result

loader = CsvLoader()
df_a, meta_a = loader.load("<arquivo_a>", encoding="utf-8", sep=";")
df_b, meta_b = loader.load("<arquivo_b>", encoding="utf-8", sep=";")

agent = IntegrationAgent(use_llm=False)  # True para acionar Claude
result = agent.run(df_a, meta_a, df_b, meta_b)

print_result(result)
saved = agent.save(result)
print(f"Resultado salvo em: {saved}")
```

Se o encoding falhar, tente `latin-1`. O `CsvLoader` aceita os mesmos parâmetros do `pd.read_csv`.

### Opção 2 — Pipeline inline (se módulos indisponíveis)

Execute os passos manualmente:

#### Passo 1: Carregar as tabelas

```python
import pandas as pd

def load_csv(path):
    try:
        return pd.read_csv(path, sep=";", encoding="utf-8", dtype=str)
    except UnicodeDecodeError:
        return pd.read_csv(path, sep=";", encoding="latin-1", dtype=str)
```

#### Passo 2: Gerar candidatos

Para cada par `(col_a, col_b)`:

1. **Score semântico** — similaridade entre os nomes + grupo de domínio compartilhado
2. **Score estrutural** — compatibilidade de dtype
3. **Match rate** — fração dos valores de A que existem em B após normalização (strip + upper + remove pontuação)

Score final: `0.35 × semântico + 0.30 × match_rate + 0.20 × estrutural + 0.15 × padrão_detectado`

Filtre pares com score semântico < 0.3. Ordene por score final decrescente e mantenha top-10.

Os grupos de domínio e padrões regex estão documentados na skill `analisar-tabela` — consulte-a se precisar da lista completa.

#### Passo 3: Construir evidências

Para cada candidato, liste:
- **Evidências favoráveis**: match rate alto, mesmo grupo de domínio, padrão regex compatível, score semântico alto
- **Evidências contrárias**: null rate alto, dtype incompatível, match rate baixo, comprimentos médios muito diferentes
- **Transformações necessárias**: normalização de case, remoção de pontuação, zfill, cast de tipo

#### Passo 4: Decidir a melhor chave

Priorize o candidato com:
1. Maior match rate normalizado
2. Mesmo grupo de domínio em ambas as colunas
3. Padrão regex compatível
4. Maior score semântico (desempate)

Se nenhum candidato simples tiver match rate > 0.5, avalie combinações de 2 colunas (chave composta) — ex: `(cd_orgao, exercicio)` vs `(CO_ORGAO, ANO)`.

#### Passo 5 (opcional): Busca de chave derivada — quando match rate < 0.5

Bases governamentais frequentemente usam identificadores que **embutem** o identificador de outro sistema em um formato mais longo. Execute esta fase quando o melhor candidato direto tiver match_rate < 0.5.

**5a — Chave embutida (substring):**

```python
# Para cada coluna de alta cardinalidade em B, tente extrair substring que case com A
for col_b in colunas_alta_cardinalidade_b:
    for col_a in colunas_alta_cardinalidade_a:
        # Testa se os valores de col_a aparecem como substring em col_b
        set_a = set(normalize(df_a[col_a].dropna()))
        match = df_b[col_b].dropna().apply(
            lambda v: any(a in normalize(pd.Series([v]))[0] for a in set_a)
        ).mean()
        if match > 0.3:
            # Identificou padrão embutido — extraia via regex e calcule match real
```

**5b — Chave reconstruível (concatenação de campos):**

Padrão comum no governo federal: o identificador SIAFI embute campos separados do sistema de origem.

```python
import re

# Padrões de identificador SIAFI conhecidos:
# NC:  [UG 6dig][gestão 5dig][ANO 4dig]NC[seq 6dig]
# NE:  [UG 6dig][gestão 5dig][ANO 4dig]NE[seq 6dig]  
# PF:  [UG 6dig][gestão 5dig][ANO 4dig]PF[seq 6dig]

def testa_reconstrucao(df_a, col_ug, col_gestao, col_id_curto, col_b_longo):
    """
    Tenta reconstruir o identificador longo de B a partir de campos de A.
    col_id_curto: ex: tx_numero_nota com formato ANONCseq
    col_ug, col_gestao: campos complementares de A
    col_b_longo: ex: nc com formato SIAFI completo
    """
    def extrair_ano_seq(s):
        m = re.match(r"(\d{4})(NC|NE|PF|OB)(\d+)", str(s).strip().upper())
        return (m.group(1), m.group(2), m.group(3).zfill(6)) if m else (None, None, None)

    ano_seq = df_a[col_id_curto].apply(extrair_ano_seq)
    df_a['_reconstruido'] = (
        df_a[col_ug].str.strip().str.zfill(6) +
        df_a[col_gestao].str.strip().str.zfill(5) +
        ano_seq.apply(lambda x: x[0] or '') +
        ano_seq.apply(lambda x: x[1] or '') +
        ano_seq.apply(lambda x: x[2] or '')
    )
    set_b = set(df_b[col_b_longo].str.strip())
    match = df_a['_reconstruido'].isin(set_b).mean()
    return match, df_a['_reconstruido']
```

**5c — Quando reportar chave derivada:**

Se a reconstrução atingir match_rate > 0.5 para algum ano/subconjunto:
- Informe que a chave não é direta — requer transformação de formato
- Descreva a fórmula de reconstrução com exemplo concreto
- Explique que match_rate baixo global pode ser cobertura temporal diferente entre sistemas
- Sugira filtrar por ano antes de fazer o join para maximizar o match

**Exemplo de saída para chave derivada:**

```
CHAVE DERIVADA IDENTIFICADA
  Fórmula: nc_siafi = cd_ug_emitente[6dig] + cd_gestao_emitente[5dig] + ANO(tx_numero_nota) + tipo + SEQ(tx_numero_nota)[6dig]
  Match 2023: 96.6%  |  Match global: 12.8% (diferença de cobertura temporal)
  Evidência: identificador SIAFI embute o identificador Transfere + campos de UG/gestão
```

---

## Formato de saída

### Terminal

```
══════════════════════════════════════════════════════════════════════
IDENTIFICAÇÃO DE CHAVE DE INTEGRAÇÃO
  Tabela A: <nome_a>  (<N> linhas, <Y> colunas)
  Tabela B: <nome_b>  (<N> linhas, <Y> colunas)
══════════════════════════════════════════════════════════════════════

TOP CANDIDATOS:
  #1  col_a ↔ col_b  | score: 0.XXX | match: XX.X% | cardinalidade: alta
      Evidências: <resumo>
      Transformações: <se houver>

  #2  ...
  ...

══════════════════════════════════════════════════════════════════════
MELHOR CHAVE IDENTIFICADA
  Tabela A : <nome_a>  →  <coluna(s)_a>
  Tabela B : <nome_b>  →  <coluna(s)_b>
  Confiança: 0.XX
  Justificativa: "<explicação objetiva>"
══════════════════════════════════════════════════════════════════════
```

### JSON (salvo em output/)

```json
{
  "summary": "",
  "candidate_keys": [
    {
      "table_a_columns": [],
      "table_b_columns": [],
      "score": 0.0,
      "match_rate": 0.0,
      "cardinality": "",
      "evidence_for": [],
      "evidence_against": [],
      "required_transformations": [],
      "decision": "best | candidate | rejected"
    }
  ],
  "best_match": {
    "table_a": "",
    "columns_a": [],
    "table_b": "",
    "columns_b": [],
    "confidence": 0.0,
    "justification": ""
  }
}
```

---

## Situações especiais

**Nenhum candidato encontrado** — Informe que nenhum par de colunas passou do limiar semântico mínimo. Sugira verificar se as tabelas têm de fato uma relação direta, ou se a integração requer uma tabela intermediária.

**Candidato melhor < 50% de match** — Acione automaticamente o Passo 5 (busca de chave derivada). Casos comuns no governo federal:
- Identificador SIAFI embute campos separados de outro sistema (NC, NE, PF: `[UG][gestão][ANO][tipo][seq]`)
- Chave curta do Transfere (`ANONCseq`) embutida na chave longa do SIAFI
- Match global baixo com match alto em subperíodo = cobertura temporal diferente, não incompatibilidade
Nesse caso, apresente a fórmula de reconstrução e o match por ano, não apenas o match global.

**Múltiplos candidatos com score parecido** — Apresente os top-3 e explique a diferença entre eles. Deixe o usuário decidir ou peça mais contexto sobre o domínio.

**Chave composta** — Se a melhor opção for uma combinação de colunas, explique claramente quais colunas compõem a chave e como concatená-las para o join.

**Match rate assimétrico** — Ex: B→A = 100% mas A→B = 40%. Informe que B é provavelmente um subconjunto de A (ex: apenas registros pagos de um universo de empenhos). Isso é esperado e não invalida a chave.

---

## Cuidados importantes

- Leia tudo como `dtype=str` para não perder zeros à esquerda em códigos de órgão, UO, NE.
- Normalize antes de comparar: strip + upper + remove `.`, `-`, `/`, espaços.
- Não descarte candidatos apenas por nome de coluna diferente — o match rate é mais confiável.
- Se o usuário mencionar que uma das tabelas é "de pagamentos" ou "de execução", isso é contexto valioso: espera-se que seja subconjunto da outra.
