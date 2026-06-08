# Gov-Hub — Sistema de Integração Semântica de Bases Governamentais

Sistema de três camadas para ingestão, transformação e integração semântica de bases de dados do governo federal brasileiro. Combina Apache Airflow, dbt e raciocínio LLM (Claude) para descobrir automaticamente chaves de integração entre tabelas de fontes distintas.

---

## Visão geral da arquitetura

```
Fontes externas (APIs, PDFs, CSVs, dumps SQL)
        ↓
┌─────────────────────────────────────────────────┐
│  ingestion/   — Apache Airflow + MinIO + DuckDB  │  ← Camada 1: Ingestão
│  Extrai, valida e armazena dados brutos           │
└────────────────────┬────────────────────────────┘
                     │ Silver Zone (DuckDB)
                     ↓
┌─────────────────────────────────────────────────┐
│  transformation/  — dbt + PostgreSQL             │  ← Camada 2: Transformação
│  Bronze → Silver → Gold (modelos analíticos)     │
└────────────────────┬────────────────────────────┘
                     │ tabelas limpas (CSV/DuckDB)
                     ↓
┌─────────────────────────────────────────────────┐
│  integration/     — Python + Claude API          │  ← Camada 3: Integração
│  Identifica chaves semânticas entre tabelas      │
└─────────────────────────────────────────────────┘
```

Cada camada é independente e pode ser usada isoladamente.

---

## Pré-requisitos globais

| Ferramenta | Versão mínima | Para que serve |
|---|---|---|
| Python | 3.11 | Camadas integration e ingestion |
| Docker + Docker Compose | 24.x | Camada ingestion (Airflow, MinIO, Postgres) |
| dbt-core + dbt-postgres | 1.x | Camada transformation |
| PostgreSQL | 14+ | Transformation (pode usar o do docker da ingestion) |
| Chave Anthropic API | — | Decision Layer e parser PDF semântico |

Obtenha a chave em: https://console.anthropic.com/settings/keys

---

## Camada 1 — Ingestion

**Localização:** `ingestion/`  
**Função:** extrai dados de fontes externas (API REST, CSV/XLSX, dump SQL, PDF) e os armazena em duas zonas:

- **Bronze Zone (MinIO)** — artefato bruto imutável, nunca sobrescrito
- **Silver Zone (DuckDB)** — tabela limpa e consultável, alimenta as camadas seguintes

### Componentes internos

| Diretório | Função |
|---|---|
| `extractors/` | Extratores para CSV/XLSX, REST API, dump SQL e download de PDF |
| `parsers/` | Parser estrutural (pdfplumber + camelot) e semântico (Claude API) |
| `storage/` | Abstrações Bronze (MinIO) e Silver (DuckDB) |
| `dags/` | Um DAG Airflow por tipo de fonte + DAG de trigger de integração |
| `configs/` | Um YAML por fonte — declara schedule, modo de extração, colunas e páginas |
| `bridge/` | Lê tabelas do DuckDB e dispara o `IntegrationAgent` |

### Setup

#### Linux / macOS

```bash
cd ingestion
cp .env.example .env
# Edite .env: preencha ANTHROPIC_API_KEY (obrigatório para parser PDF semântico)

make init      # inicializa banco do Airflow e cria usuário admin
make up        # sobe todos os serviços (Airflow, MinIO, PostgreSQL)
make bucket    # cria bucket bronze no MinIO
```

#### Windows (PowerShell)

```powershell
cd ingestion
Copy-Item .env.example .env
# Edite .env com ANTHROPIC_API_KEY

docker compose up airflow-init   # equivale ao make init
docker compose up -d             # equivale ao make up

# Criar bucket manualmente após subir:
docker compose exec minio mc alias set local http://localhost:9000 minioadmin minioadmin
docker compose exec minio mc mb --ignore-existing local/bronze
```

### Variáveis de ambiente (`ingestion/.env`)

| Variável | Padrão | Descrição |
|---|---|---|
| `MINIO_ACCESS_KEY` | `minioadmin` | Usuário MinIO |
| `MINIO_SECRET_KEY` | `minioadmin` | Senha MinIO |
| `MINIO_BUCKET_BRONZE` | `bronze` | Nome do bucket Bronze |
| `DUCKDB_PATH` | `/opt/airflow/data/silver.duckdb` | Caminho do arquivo DuckDB no container |
| `ANTHROPIC_API_KEY` | — | **Obrigatório** para parser PDF semântico |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Modelo usado no parser semântico |

### Acessar as interfaces

| Interface | URL | Credenciais |
|---|---|---|
| Airflow UI | http://localhost:8080 | admin / admin |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin |

### Adicionar uma nova fonte

1. Crie `configs/<nome_da_fonte>.yaml` seguindo um dos exemplos existentes em `configs/`
2. O DAG correspondente detecta o arquivo automaticamente no próximo tick do scheduler
3. Nenhuma alteração de código necessária

### Comandos úteis

```bash
make logs     # acompanha logs do scheduler e webserver
make down     # derruba todos os serviços
```

---

## Camada 2 — Transformation

**Localização:** `transformation/`  
**Função:** modelos dbt que movem os dados pela medalha Bronze → Silver → Gold, enriquecendo e normalizando progressivamente.

| Camada | Materialização | Schema PostgreSQL | Descrição |
|---|---|---|---|
| Bronze | incremental | `bronze` | Dados brutos carregados sem alteração |
| Silver | table | `silver` | Dados limpos, enriquecidos, tipados |
| Gold | table | `gold` | Modelos analíticos prontos para consumo |

### Setup

#### Linux / macOS

```bash
# Use o PostgreSQL já iniciado pelo docker-compose da ingestion, ou suba um próprio.
cd transformation
cp .env.example .env
# Edite .env com as credenciais do PostgreSQL

pip install dbt-core dbt-postgres

dbt deps           # instala pacotes (astronomer-cosmos etc.)
dbt debug          # verifica conexão
dbt run            # executa todos os modelos
dbt test           # roda os testes de qualidade
```

#### Windows (PowerShell)

```powershell
cd transformation
Copy-Item .env.example .env
# Edite .env com credenciais do PostgreSQL

pip install dbt-core dbt-postgres

dbt deps
dbt debug
dbt run
dbt test
```

### Variáveis de ambiente (`transformation/.env`)

| Variável | Descrição |
|---|---|
| `POSTGRES_HOST` | Host do PostgreSQL (padrão: `localhost`) |
| `POSTGRES_PORT` | Porta (padrão: `5432`) |
| `POSTGRES_USER` | Usuário do banco |
| `POSTGRES_PASSWORD` | Senha do banco |
| `POSTGRES_DB` | Nome do banco (padrão: `govhub`) |

### Comandos úteis

```bash
dbt run --select bronze     # só modelos Bronze
dbt run --select silver     # só modelos Silver
dbt run --select gold       # só modelos Gold
dbt run --select +modelo    # modelo + todos os seus ancestrais
dbt docs generate && dbt docs serve   # documentação interativa em http://localhost:8080
```

---

## Camada 3 — Integration

**Localização:** `integration/`  
**Função:** identifica automaticamente a melhor chave de junção entre dois arquivos CSV usando análise semântica, estatística e raciocínio LLM.

### Pipeline de 5 etapas

```
Etapa 0 — Validar Contexto      verifica cobertura do Domain Context (≥ 60%)
Etapa 1 — Perfilar Tabelas      dtype, cardinalidade, nulos, unicidade, top valores
Etapa 2 — Evidence Layer        compara pares de colunas candidatos (semântico + estatístico)
Etapa 3 — Decision Layer        LLM raciocina sobre as evidências e elege a Integration Key
Etapa 4 — Relatório             gera HTML com gauge de confiança, código Python e SQL prontos
```

### Setup

#### Linux / macOS

```bash
cd integration
cp ../.env.example .env
# Edite .env: preencha ANTHROPIC_API_KEY

pip install -e .              # instala o pacote em modo editável
# ou, para desenvolvimento:
pip install -e ".[dev]"

# Verificar instalação:
python -c "from src.config.context_loader import load_context; print('ok')"
```

#### Windows (PowerShell)

```powershell
cd integration
Copy-Item ..\.env.example .env
# Edite .env com ANTHROPIC_API_KEY

pip install -e .

# Verificar instalação:
python -c "from src.config.context_loader import load_context; print('ok')"
```

### Variáveis de ambiente (`.env` na raiz ou em `integration/`)

| Variável | Obrigatório | Padrão | Descrição |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Sim (para LLM) | — | Chave da API Anthropic |
| `MODEL_NAME` | Não | `claude-sonnet-4-6` | Modelo usado na Decision Layer |
| `MIN_MATCH_RATE` | Não | `0.5` | Match rate mínimo para aceitar um candidato |
| `MIN_CONFIDENCE` | Não | `0.6` | Confiança mínima para promover a Integration Key |
| `MAX_CANDIDATE_KEYS` | Não | `10` | Máximo de candidatos enviados ao LLM |
| `SAMPLE_SIZE` | Não | `1000` | Linhas amostradas na Evidence Layer |

### Executar via terminal

```bash
# Com raciocínio LLM (padrão)
python main.py --table-a data/raw/tabela_a.csv --table-b data/raw/tabela_b.csv

# Sem LLM (só análise estatística — mais rápido, sem custo de API)
python main.py --table-a data/raw/tabela_a.csv --table-b data/raw/tabela_b.csv --no-llm

# Salvando resultado em caminho específico
python main.py --table-a data/raw/tabela_a.csv --table-b data/raw/tabela_b.csv \
               --output output/meu_resultado.json
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

> `main.py` executa a mesma lógica do `/integrar-bases`, mas sem gerar o relatório HTML — só o JSON com a Integration Key identificada.

### Executar via Claude Code (skills)

Com o Claude Code aberto na raiz do projeto, use as skills abaixo diretamente no chat.

#### `/integrar-bases` — pipeline completo entre dois CSVs

```
/integrar-bases data/raw/tabela_a.csv data/raw/tabela_b.csv
/integrar-bases data/raw/tabela_a.csv data/raw/tabela_b.csv --context output/contexts/context_dominio.json
```

Executa todas as 5 etapas e gera `output/reports/relatorio_{a}__{b}_{data}.html`.

---

#### `/mapear-integracoes` — descoberta automática em lote

```
/mapear-integracoes data/raw/mir-simple-db/
/mapear-integracoes data/raw/mir-simple-db/ --context output/contexts/context_orcamento_federal.json
```

Analisa todos os CSVs do diretório, calcula afinidade semântica entre todos os pares possíveis, filtra os que têm afinidade ≥ 0.45 e executa o pipeline completo só nos aprovados.

**Output:**
- `output/mapa_integracoes_{dir}_{data}.json`
- `output/reports/mapa_integracoes_{dir}_{data}.html`
- `output/reports/relatorio_{a}__{b}_{data}.html` (um por par aprovado)

---

#### `/definir-contexto` — gerador de Domain Context

```
/definir-contexto "bases de saúde pública do SUS: estabelecimentos, internações, procedimentos"
/definir-contexto "registros do MEC: escolas, matrículas, professores" data/raw/escolas.csv data/raw/matriculas.csv
```

Gera `output/contexts/context_{dominio}.json` reutilizável em todas as integrações do domínio. Fornecer CSVs de exemplo melhora a qualidade. Use antes de integrar bases de um domínio novo ou quando o pipeline reportar cobertura < 60%.

---

#### `/analisar-tabela` — perfilador de tabela

```
/analisar-tabela data/raw/tabela.csv
/analisar-tabela data/raw/tabela.csv --context output/contexts/context_dominio.json
```

Perfila uma tabela: dtype, cardinalidade, nulos, unicidade, top valores, grupo de domínio e padrão regex por coluna. Sugere candidatas a chave primária. Output: `output/analisar_tabela_{stem}.json`.

---

#### `/comparar-colunas` — Evidence Layer manual

```
/comparar-colunas data/raw/empenhos.csv:nr_empenho data/raw/nc.csv:nc
```

Compara dois campos específicos e retorna evidências de compatibilidade. Útil para validar uma hipótese antes de rodar o pipeline completo.

---

#### `/identificar-chave` — Decision Layer isolada

```
/identificar-chave data/raw/tabela_a.csv data/raw/tabela_b.csv
/identificar-chave data/raw/tabela_a.csv data/raw/tabela_b.csv --no-llm
```

Produz só o JSON com a Integration Key, sem relatório HTML. Output: `output/identificar_chave_{a}__{b}.json`.

---

#### `/gerar-relatorio` — relatório HTML a partir de JSON existente

```
/gerar-relatorio output/identificar_chave_empenhos__nc.json
/gerar-relatorio output/identificar_chave_empenhos__nc.json --context output/contexts/context_orcamento_federal.json
```

Gera `output/reports/relatorio_{a}__{b}_{data}.html` com gauge de confiança, tabela de candidatos, evidências e código Python/SQL prontos.

---

### Quando usar cada skill

| Situação | Skill |
|---|---|
| Integrar duas bases do início ao fim | `/integrar-bases a.csv b.csv` |
| Descobrir quais bases de um diretório se relacionam | `/mapear-integracoes diretorio/` |
| Explorar uma tabela antes de integrar | `/analisar-tabela tabela.csv` |
| Testar se dois campos específicos casam | `/comparar-colunas a.csv:campo b.csv:campo` |
| Só a chave, sem relatório | `/identificar-chave a.csv b.csv` |
| Regerar relatório de uma análise existente | `/gerar-relatorio output/identificar_chave_....json` |
| Primeiro uso em domínio novo (saúde, educação...) | `/definir-contexto "descrição"` antes |

---

### Fluxo de comunicação entre skills

As skills trocam dados via arquivo — o output de uma etapa é lido como input pela próxima.

```
/definir-contexto  ──→  output/contexts/context_{dominio}.json
                                  ↓
/mapear-integracoes ──→ filtra pares ≥ 0.45 → chama /integrar-bases para cada par aprovado
                                  ↓
/integrar-bases ─────────────────────────────────────────────────────────────────────┐
    ↓ Etapa 0: valida contexto                                                        │
    ↓ Etapa 1: /analisar-tabela A  → output/analisar_tabela_{a}.json                 │
    ↓          /analisar-tabela B  → output/analisar_tabela_{b}.json                 │
    ↓ Etapa 2: /comparar-colunas   → output/comparar_colunas_{a}__{b}.json           │
    ↓ Etapa 3: /identificar-chave  → output/identificar_chave_{a}__{b}.json          │
    ↓ Etapa 4: /gerar-relatorio    → output/reports/relatorio_{a}__{b}_{data}.html ←─┘
```

Cada arquivo intermediário fica em `output/` e pode ser inspecionado manualmente. Se uma etapa falhar, o pipeline pode ser retomado a partir do ponto de falha.

---

### Estrutura de arquivos gerados

```
output/
├── contexts/
│   └── context_{dominio}.json          ← /definir-contexto
├── analisar_tabela_{stem}.json          ← /analisar-tabela
├── comparar_colunas_{a}__{b}.json       ← /comparar-colunas (automático)
├── comparar_colunas_{a}_{col}__{b}_{col}.json  ← /comparar-colunas (manual)
├── identificar_chave_{a}__{b}.json      ← /identificar-chave
└── reports/
    ├── relatorio_{a}__{b}_{data}.html   ← /gerar-relatorio
    └── mapa_integracoes_{dir}_{data}.html  ← /mapear-integracoes
```

---

### Domain Context

O Domain Context descreve o vocabulário semântico de um domínio: quais nomes de coluna significam a mesma coisa (ex: `nr_empenho`, `num_empenho`, `nota_empenho` → grupo `empenho`) e quais são os padrões de identificadores (ex: `^\d{4}NE\d{6}$`).

**Sem contexto declarado** o pipeline usa os defaults do domínio orçamentário federal brasileiro (SIAFI, Transfere, Portal da Transparência).

**Com contexto declarado** via `--context`, o pipeline reconhece os grupos do domínio informado e produz resultados mais precisos. O pipeline avisa quando a cobertura está abaixo de 60% — sinal de que o contexto precisa ser atualizado.

---

## Estrutura do repositório

```
gov-hub/
├── ingestion/              # Camada 1 — Airflow, MinIO, DuckDB
│   ├── configs/            # YAMLs de fontes de dados
│   ├── dags/               # DAGs Airflow
│   ├── extractors/         # Extratores (API, CSV, SQL dump, PDF)
│   ├── parsers/            # Parsers estrutural e semântico de PDF
│   ├── storage/            # Abstrações Bronze e Silver
│   ├── bridge/             # Bridge DuckDB → IntegrationAgent
│   ├── docker-compose.yml
│   ├── Makefile
│   └── requirements.txt
│
├── transformation/         # Camada 2 — dbt + PostgreSQL
│   ├── models/
│   │   ├── bronze/         # Modelos incrementais (raw)
│   │   ├── silver/         # Tabelas limpas e enriquecidas
│   │   └── gold/           # Modelos analíticos finais
│   ├── macros/
│   ├── tests/
│   ├── seeds/
│   ├── dbt_project.yml
│   └── profiles.yml
│
├── integration/            # Camada 3 — Agente semântico Python
│   ├── src/
│   │   ├── agent/          # Orchestrator, candidate generator, LLM reasoner
│   │   ├── analyzers/      # Structural, semantic, statistical, content analyzers
│   │   ├── transformers/   # Pattern detector, normalizer
│   │   ├── loaders/        # CSV loader
│   │   └── config/         # Domain config, settings, context loader
│   ├── data/               # Dados de entrada (CSVs)
│   ├── output/             # JSONs e HTMLs gerados
│   ├── tests/
│   ├── main.py
│   └── pyproject.toml
│
├── docs/                   # Documentação de arquitetura
├── analises/               # Saídas de análises do TCC
├── CONTEXT.md              # Glossário e vocabulário do domínio
└── README.md               # Este arquivo
```

---

## Fluxos de uso comuns

### Integrar um diretório inteiro

```
/mapear-integracoes data/raw/mir-simple-db/
```

### Integração completa entre dois CSVs

```
/integrar-bases tabela_a.csv tabela_b.csv
```

### Primeiro uso em domínio novo

```
/definir-contexto "descrição do seu domínio" exemplo_a.csv exemplo_b.csv
/integrar-bases tabela_a.csv tabela_b.csv --context output/contexts/context_{dominio}.json
```

### Exploração antes de integrar

```
/analisar-tabela tabela_a.csv
/analisar-tabela tabela_b.csv
/comparar-colunas tabela_a.csv:campo_suspeito tabela_b.csv:outro_campo
```

### Pipeline via terminal (Linux/macOS)

```bash
cd integration
python main.py --table-a data/raw/tabela_a.csv --table-b data/raw/tabela_b.csv
```

### Pipeline via terminal (Windows)

```powershell
cd integration
python main.py --table-a data\raw\tabela_a.csv --table-b data\raw\tabela_b.csv
```

---

## Solução de problemas frequentes

### `ModuleNotFoundError: No module named 'src'`

O pacote não foi instalado. Execute na raiz do diretório `integration/`:

```bash
pip install -e .
```

### Etapa LLM retorna erro de autenticação

Verifique se `ANTHROPIC_API_KEY` está definida no `.env` e se o arquivo está na raiz do projeto ou em `integration/`:

```bash
# Linux/macOS
grep ANTHROPIC_API_KEY .env

# Windows
Select-String -Path .env -Pattern "ANTHROPIC_API_KEY"
```

### Airflow não sobe / porta 8080 ocupada

Verifique se há outro processo usando a porta:

```bash
# Linux/macOS
lsof -i :8080

# Windows
netstat -ano | findstr :8080
```

Altere `ports` no `docker-compose.yml` se necessário.

### MinIO bucket não existe

Execute `make bucket` (Linux/macOS) ou o comando equivalente do Windows listado na seção de setup da ingestion.

### dbt não conecta ao PostgreSQL

Verifique as variáveis em `transformation/.env` e confirme que o PostgreSQL está acessível:

```bash
dbt debug
```

### Coverage do contexto abaixo de 60%

O pipeline detecta automaticamente e avisa. Execute `/definir-contexto` com uma descrição do domínio para gerar um contexto mais preciso.
