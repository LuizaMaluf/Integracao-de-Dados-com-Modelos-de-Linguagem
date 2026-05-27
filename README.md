# Sistema de Integração Semântica de Bases de Dados

Identifica automaticamente chaves de integração entre dois arquivos CSV usando análise semântica, estatística e raciocínio com LLM. Gera um relatório HTML com a Integration Key recomendada, evidências e código de implementação pronto.

---

## Como rodar

### Rodar tudo de uma vez

Digite no chat do Claude Code:

```
/mapear-integracoes data/raw/mir-simple-db/
```

Isso analisa todos os CSVs do diretório, descobre automaticamente quais bases têm relação entre si, e executa o pipeline completo só nos pares relevantes. Os relatórios ficam em `output/reports/`.

### Rodar um par específico

```
/integrar-bases data/raw/mir-simple-db/empenhos_tesouro_ted_202605211520.csv data/raw/mir-simple-db/nc_tesouro_mir_202605211521.csv
```

### Rodar via terminal (sem Claude Code)

Você também pode chamar o pipeline diretamente pelo terminal com `python main.py`:

```bash
python main.py --table-a data/raw/tabela_a.csv --table-b data/raw/tabela_b.csv
```

**Parâmetros disponíveis:**

| Parâmetro | Obrigatório | Descrição |
|---|---|---|
| `--table-a` | Sim | Caminho para o CSV da tabela A |
| `--table-b` | Sim | Caminho para o CSV da tabela B |
| `--name-a` | Não | Nome de exibição da tabela A |
| `--name-b` | Não | Nome de exibição da tabela B |
| `--sep` | Não | Separador CSV (padrão: `;`) |
| `--encoding` | Não | Encoding do CSV (padrão: `utf-8`) |
| `--no-llm` | Não | Pula a etapa de raciocínio com LLM |
| `--output` | Não | Caminho para salvar o JSON de saída |

**Exemplos:**
```bash
# Com LLM (padrão)
python main.py --table-a data/raw/mir-simple-db/empenhos_tesouro_ted_202605211520.csv \
               --table-b data/raw/mir-simple-db/nc_tesouro_mir_202605211521.csv

# Sem LLM (só análise estatística)
python main.py --table-a data/raw/mir-simple-db/empenhos_tesouro_ted_202605211520.csv \
               --table-b data/raw/mir-simple-db/nc_tesouro_mir_202605211521.csv \
               --no-llm

# Salvando o resultado em um arquivo específico
python main.py --table-a data/raw/tabela_a.csv --table-b data/raw/tabela_b.csv \
               --output output/meu_resultado.json
```

> O `main.py` executa a mesma lógica do `/integrar-bases`, mas sem gerar o relatório HTML — só o JSON com a Integration Key identificada.

### Pré-requisito

O ambiente Python precisa estar configurado. Para verificar:

```bash
python -c "from src.config.context_loader import load_context; print('ok')"
```

Se retornar `ok`, está pronto. Caso contrário, instale as dependências:

```bash
pip install -e .
```

---

## Skills disponíveis

### `/mapear-integracoes` — Mapeador de integrações em lote

Descobre quais bases de um diretório podem ser integradas entre si, sem precisar especificar pares manualmente. Analisa todos os CSVs, calcula score semântico entre todos os pares possíveis, filtra os que têm potencial real e executa o pipeline completo apenas nesses — evitando execuções desnecessárias.

**Quando usar:** quando você tem um diretório com várias bases e quer descobrir quais se relacionam, ou quando quer rodar o pipeline em lote.

**Como chamar:**
```
/mapear-integracoes data/raw/mir-simple-db/

/mapear-integracoes data/raw/mir-simple-db/ --context output/contexts/context_orcamento_federal.json
```

**O que faz, em ordem:**
1. Lê os nomes das colunas de todos os CSVs (sem carregar os dados)
2. Calcula score de afinidade semântica entre todos os C(N,2) pares
3. Filtra pares com afinidade ≥ 0.45 — descarta combinações sem relação real
4. Executa o pipeline completo (`/integrar-bases`) apenas nos pares aprovados
5. Gera um mapa HTML com todas as integrações encontradas e links para os relatórios

**Output:**
- `output/mapa_integracoes_{dir}_{data}.json` — mapa completo em JSON
- `output/reports/mapa_integracoes_{dir}_{data}.html` — mapa visual com cards e links
- `output/reports/relatorio_{a}__{b}_{data}.html` — um relatório por par aprovado

---

### `/integrar-bases` — Orquestradora do pipeline

Executa o pipeline completo entre dois CSVs. É o ponto de entrada principal.

**Quando usar:** sempre que quiser integrar duas bases do início ao fim sem rodar etapas manualmente.

**Como chamar:**
```
/integrar-bases <tabela_a.csv> <tabela_b.csv>
/integrar-bases <tabela_a.csv> <tabela_b.csv> --context output/contexts/context_saude_sus.json
```

**O que faz, em ordem:**
1. Valida o Domain Context (ou usa defaults orçamentários)
2. Perfila as duas tabelas
3. Seleciona e compara automaticamente os pares de colunas candidatos
4. Decide a melhor Integration Key com raciocínio LLM
5. Gera o relatório HTML

**Output final:** `output/reports/relatorio_{a}__{b}_{data}.html`

---

### `/definir-contexto` — Gerador de Domain Context

Cria um arquivo JSON reutilizável que descreve o vocabulário semântico de um domínio — grupos de colunas equivalentes e padrões de identificadores. Gerado uma vez por domínio, reutilizado em todas as integrações subsequentes.

**Quando usar:** antes de integrar bases de um domínio novo (saúde, educação, tributário, etc.), ou quando o pipeline reportar cobertura de contexto abaixo de 60%.

**Como chamar:**
```
/definir-contexto "bases de saúde pública do SUS: estabelecimentos, internações, procedimentos, CID"

/definir-contexto "dados de IPTU e ITBI municipal: imóveis, contribuintes, lançamentos, pagamentos"

/definir-contexto "registros do MEC: escolas, matrículas, professores, turmas" data/raw/escolas.csv data/raw/matriculas.csv
```

Fornecer os CSVs de exemplo melhora a qualidade dos grupos gerados.

**Output:** `output/contexts/context_{dominio}.json`

---

### `/analisar-tabela` — Perfilador de tabela

Perfila uma tabela CSV: dtype, cardinalidade, nulos, unicidade, top valores, comprimento médio, grupo de domínio e padrão regex de cada coluna. Sugere candidatas a chave primária.

**Quando usar:** para explorar uma tabela nova antes de integrar, ou para entender sua estrutura sem precisar rodar o pipeline completo.

**Como chamar:**
```
/analisar-tabela data/raw/mir-simple-db/planos_acao_ted_202605211522.csv

/analisar-tabela data/raw/mir-simple-db/programas_ted_202605211522.csv --context output/contexts/context_orcamento_federal.json
```

**Output:** `output/analisar_tabela_{stem}.json`

---

### `/comparar-colunas` — Comparador de colunas (Evidence Layer)

Opera em dois modos:

**Modo automático** — invocado pelo `/integrar-bases`. Lê os JSONs do `/analisar-tabela` e seleciona automaticamente os pares mais prováveis para comparar. Produz as evidências que a Decision Layer vai consumir.

**Modo manual** — você especifica exatamente quais colunas comparar. Útil para testar uma hipótese antes de rodar o pipeline completo.

**Quando usar o modo manual:** quando quiser validar rapidamente se dois campos específicos são compatíveis — "esse `nr_convenio` casa com esse `cd_convenio`?"

**Como chamar (modo manual):**
```
/comparar-colunas data/raw/mir-simple-db/empenhos_tesouro_ted_202605211520.csv:nr_empenho data/raw/mir-simple-db/nc_tesouro_mir_202605211521.csv:nc

/comparar-colunas data/raw/mir-simple-db/planos_acao_ted_202605211522.csv:nr_convenio data/raw/mir-simple-db/programas_ted_202605211522.csv:nr_convenio
```

**Output:**
- Modo automático: `output/comparar_colunas_{a}__{b}.json`
- Modo manual: `output/comparar_colunas_{a}_{col_a}__{b}_{col_b}.json`

---

### `/identificar-chave` — Identificador de Integration Key (Decision Layer)

Decide a melhor Integration Key entre duas tabelas usando raciocínio LLM. Quando invocado diretamente pelo usuário, executa o pipeline de evidências internamente. Quando invocado pelo `/integrar-bases`, lê as evidências já produzidas pelo `/comparar-colunas`.

Inclui busca de **Derived Key**: quando nenhuma chave direta tem match > 50%, testa reconstrução de identificadores SIAFI (NC, NE, PF) e identifica chaves embutidas como substring.

**Quando usar diretamente:** quando quiser só a identificação da chave, sem relatório.

**Como chamar:**
```
/identificar-chave data/raw/mir-simple-db/pf_transfere_mir_202605211521.csv data/raw/mir-simple-db/planos_acao_ted_202605211522.csv

/identificar-chave data/raw/mir-simple-db/nc_tesouro_mir_202605211521.csv data/raw/mir-simple-db/notas_de_credito_202605211521.csv --no-llm
```

**Output:** `output/identificar_chave_{a}__{b}.json`

---

### `/gerar-relatorio` — Gerador de relatório HTML

Gera uma página HTML estilizada a partir do resultado do `/identificar-chave`. Inclui: Integration Key recomendada, gauge de confiança, tabela de candidatos com score bars, evidências, código Python e SQL prontos, e métricas de qualidade do join.

**Quando usar:** para documentar uma decisão de integração, compartilhar resultados, ou gerar evidência para o TCC.

**Como chamar:**
```
/gerar-relatorio output/identificar_chave_empenhos_tesouro_ted__nc_tesouro_mir.json

/gerar-relatorio output/identificar_chave_pf_transfere_mir__planos_acao_ted.json --context output/contexts/context_orcamento_federal.json
```

**Output:** `output/reports/relatorio_{a}__{b}_{data}.html`

---

## Quando usar cada skill

| Situação | Skill |
|---|---|
| Quero integrar duas bases específicas | `/integrar-bases a.csv b.csv` |
| Tenho um diretório e não sei quais bases se relacionam | `/mapear-integracoes diretorio/` |
| Quero explorar uma tabela antes de integrar | `/analisar-tabela tabela.csv` |
| Quero testar se dois campos específicos casam | `/comparar-colunas a.csv:campo b.csv:campo` |
| Quero só a chave, sem relatório | `/identificar-chave a.csv b.csv` |
| Quero regerar o relatório de uma análise existente | `/gerar-relatorio output/identificar_chave_....json` |
| Vou usar bases de um domínio novo (saúde, educação...) | `/definir-contexto "descrição do domínio"` primeiro |

---

## Como as skills se comunicam

As skills trocam dados **via arquivo** — o output de uma etapa é lido como input pela próxima. Os paths são previsíveis e derivados dos nomes das tabelas de entrada.

```
[definir-contexto]  ←── use antes de integrar um domínio novo
      │
      └─→  output/contexts/context_{dominio}.json

[mapear-integracoes]  ←── use com um diretório de bases
      │
      ├─→ score semântico entre todos os C(N,2) pares (só nomes de colunas)
      ├─→ descarta pares com afinidade < 0.45
      └─→ chama [integrar-bases] para cada par aprovado
               └─→ output/reports/mapa_integracoes_{dir}_{data}.html

[integrar-bases]  ←── use com dois CSVs específicos
      │
      └─→  output/contexts/context_{dominio}.json
                    │
                    ▼
[integrar-bases] ──────────────────────────────────────────────────────
      │
      │  Etapa 0: valida cobertura do contexto
      │  Etapa 1: ─→ [analisar-tabela] ×2
      │                  └─→ output/analisar_tabela_{stem_a}.json
      │                  └─→ output/analisar_tabela_{stem_b}.json
      │
      │  Etapa 2: ─→ [comparar-colunas] (modo automático)
      │                  lê: analisar_tabela_{a}.json + analisar_tabela_{b}.json
      │                  └─→ output/comparar_colunas_{a}__{b}.json
      │
      │  Etapa 3: ─→ [identificar-chave] (Decision Layer)
      │                  lê: comparar_colunas_{a}__{b}.json
      │                  └─→ output/identificar_chave_{a}__{b}.json
      │
      │  Etapa 4: ─→ [gerar-relatorio]
      │                  lê: identificar_chave_{a}__{b}.json
      │                  └─→ output/reports/relatorio_{a}__{b}_{data}.html
      │
      └──────────────────────────────────────────────────────────────────
```

Cada arquivo intermediário fica em `output/` e pode ser inspecionado manualmente. Se uma etapa falhar, o pipeline pode ser retomado do ponto de falha sem reprocessar tudo.

---

## Estrutura de arquivos gerados

```
output/
├── contexts/
│   └── context_{dominio}.json          ← gerado por /definir-contexto
├── analisar_tabela_{stem}.json          ← gerado por /analisar-tabela
├── comparar_colunas_{a}__{b}.json       ← gerado por /comparar-colunas
├── identificar_chave_{a}__{b}.json      ← gerado por /identificar-chave
└── reports/
    └── relatorio_{a}__{b}_{data}.html   ← gerado por /gerar-relatorio
```

---

## Domain Context

O Domain Context descreve o vocabulário semântico de um domínio: quais nomes de coluna significam a mesma coisa (ex: `nr_empenho`, `num_empenho`, `nota_empenho` → grupo `empenho`) e quais são os padrões de identificadores (ex: `^\d{4}NE\d{6}$`).

**Sem contexto declarado**, o pipeline usa os defaults do domínio orçamentário federal brasileiro (SIAFI, Transfere, Portal da Transparência).

**Com contexto declarado** via `--context`, o pipeline reconhece os grupos do domínio informado e produz resultados mais precisos.

O contexto é **reutilizável**: gerado uma vez com `/definir-contexto`, serve para todas as integrações subsequentes do mesmo domínio. O pipeline avisa quando a cobertura do contexto sobre as tabelas de entrada está abaixo de 60% — sinal de que o contexto precisa ser atualizado.

---

## Fluxos de uso comuns

**Integrar um diretório inteiro:**
```
/mapear-integracoes data/raw/mir-simple-db/
```

**Integração completa entre dois CSVs:**
```
/integrar-bases tabela_a.csv tabela_b.csv
```

**Primeiro uso em domínio novo:**
```
/definir-contexto "descrição do seu domínio" exemplo_a.csv exemplo_b.csv
/integrar-bases tabela_a.csv tabela_b.csv --context output/contexts/context_{dominio}.json
```

**Exploração antes de integrar:**
```
/analisar-tabela tabela_a.csv
/analisar-tabela tabela_b.csv
/comparar-colunas tabela_a.csv:campo_suspeito tabela_b.csv:outro_campo
```

**Só a chave, sem relatório:**
```
/identificar-chave tabela_a.csv tabela_b.csv
```

**Regerar relatório de uma análise existente:**
```
/gerar-relatorio output/identificar_chave_{a}__{b}.json
```
