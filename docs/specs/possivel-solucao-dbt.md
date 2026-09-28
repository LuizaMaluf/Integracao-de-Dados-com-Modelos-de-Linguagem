# Possível Solução — Integração dbt no gov-hub

## Contexto

João Egewarth (LAPPIS) trouxe a problemática do setup atual deles com Astronomer:
o Astronomer implanta **tudo** que está no repositório. Para evitar que órgãos recebam
DAGs que não são deles, a solução do time foi separar os projetos dbt por repositório
git (submodules), com um `packages.yml` central apontando para cada um.

---

## O problema que as duas abordagens resolvem

> "Nem todos os órgãos vão usar todos os modelos — e o Airflow/Astronomer não pode
> receber DAGs de órgãos que não fazem parte do deploy."

| Abordagem | Mecanismo de controle |
|---|---|
| João (submodules) | Separação estrutural — o que não está no repo não roda |
| gov-hub (DAG Factory) | Separação por configuração — o que não está no registry não é gerado |

---

## Solução proposta para o gov-hub

### Camada de transformação dbt

Manter tudo em **um único repositório**. Organizar os projetos dbt como
**pacotes locais** dentro de `transformation/dbt_packages/`:

```
transformation/
├── dbt_project.yml       (root, referencia os pacotes)
├── packages.yml          (declara pacotes locais)
├── profiles.yml
└── dbt_packages/
    ├── mir/
    │   ├── dbt_project.yml   (name: 'mir')
    │   └── models/
    │       ├── bronze/
    │       ├── silver/
    │       └── gold/
    └── ipea/
        ├── dbt_project.yml   (name: 'ipea')
        └── models/
```

```yaml
# packages.yml
packages:
  - local: dbt_packages/mir
  - local: dbt_packages/ipea
```

O `astronomer-cosmos` (já presente no projeto) cria **um DAG por pacote local**
automaticamente — sem precisar de arquivo Python de DAG por órgão.

### Camada de ingestão

Continua como está: **DAG Factory** (scripts Python config-driven) lendo o
`source_registry.yml` de cada órgão. O DAG Factory só gera DAG para o que está
declarado — sem submodule, sem fragmentação de repositório.

---

## Divisão de responsabilidades final

| Camada | Tecnologia | Controle de isolamento |
|---|---|---|
| Ingestão (extract → bronze → silver) | DAG Factory + Source Registry | YAML por órgão no registry |
| Transformação (bronze → silver → gold) | cosmos + dbt local packages | pasta por órgão em `dbt_packages/` |

---

## O que precisa ser feito

1. Reorganizar `transformation/models/` (hoje misturado) em `dbt_packages/<orgao>/`
2. Atualizar `packages.yml` para referenciar os pacotes locais
3. Remover `transformation_dag.py` manual — o cosmos assume a geração das DAGs
4. Estender o Source Registry para declarar quais pacotes dbt cada órgão usa
   (para que o DAG Factory saiba o que acionar)

---

## Por que não submodules

- Submodule resolve o problema **estruturalmente**: repositórios separados por órgão
- gov-hub resolve o mesmo problema **por configuração**: registry central por órgão
- Submodules adicionam overhead de versionamento distribuído (branches, tags, sincronização)
- Com DAG Factory, um único repo, um único ponto de versionamento e deploy

---

## Estado atual do DAG Factory

Hoje são scripts Python individuais por tipo de fonte (`api_dag.py`, `csv_xlsx_dag.py` etc.)
que fazem `glob` no diretório de configs. O ADR 0002 propõe migrar para a biblioteca
`astronomer/dag-factory` (open source, mantida pelo Astronomer), que lê um
`dag_factory.yaml` central e gera tudo automaticamente — sem Python por fonte.

---

## Skills Astronomer validados

Referência: [astronomer/agents — skills](https://github.com/astronomer/agents/tree/main/skills)

### Adotar

**cosmos-dbt-core**
Oferece três modos de integração dbt+Airflow: `DbtDag` (DAG independente), `DbtTaskGroup`
(embutido num DAG existente) e operadores individuais. Para o gov-hub, o padrão correto é
`DbtTaskGroup` — permite que ingestão e transformação vivam no mesmo DAG por órgão, com
dependência explícita entre as fases. Em produção (Astronomer), usar `DBT_MANIFEST` como
render mode: mais rápido e estável do que parsear o projeto em runtime.

**dag-factory**
Biblioteca que gera DAGs a partir de YAML declarativo. É exatamente o que o ADR 0002 propõe.
Substitui todos os scripts Python de ingestão por um único arquivo `dag_factory.yaml` e um
loader mínimo:
```python
# dags/load_dags.py
from dagfactory import load_yaml_dags
load_yaml_dags(globals_dict=globals(), dags_folder="/opt/airflow/configs")
```
Suporta `inlets`/`outlets` para data-aware scheduling nativo.

**annotating-task-lineage**
`inlets`/`outlets` com objetos `Dataset` do OpenLineage substituem o `ExternalTaskSensor`.
A task `stage_silver` declara que produziu `Dataset("silver://mir_empenhos")`; a DAG dbt
declara que consome esse dataset — o Airflow dispara a transformação automaticamente, sem
acoplamento por `dag_id` ou schedule fixo:
```python
@task(outlets=[Dataset("silver://mir_empenhos")])
def stage_silver(...): ...

transformation_dag = DbtDag(..., schedule=[Dataset("silver://mir_empenhos")])
```
Como bônus, a linhagem fica visível nativamente na aba Lineage do Astro UI.

**deploying-airflow**
`astro deploy --dags` faz deploy apenas dos arquivos de DAG sem rebuildar a imagem Docker —
ciclo de CI/CD muito mais rápido. Relevante quando o projeto migrar de Docker Compose para
Astronomer.

---

### Considerar

**checking-freshness**
Verifica se os dados silver estão frescos antes de acionar o `DbtTaskGroup`. Pode virar uma
task de guarda no início da fase de transformação — evita rodar dbt sobre dados incompletos
quando a ingestão falhou silenciosamente.

**profiling-tables**
Padrão de 7 etapas (metadados, tamanho, cardinalidade, qualidade, amostras). O skill
`analisar-tabela` do gov-hub já cobre esse escopo — a validação confirma que o padrão
está alinhado com o mercado.

**tracing-upstream-lineage**
Se `inlets`/`outlets` forem adotados (ver acima), a linhagem upstream fica disponível
gratuitamente na interface do Astro — sem trabalho adicional.

**warehouse-init**
Gera um `warehouse.md` versionável como catálogo do banco. Complementa o `Table Catalog`
(`catalog.ingested_tables`) já previsto na arquitetura do gov-hub.

---

## Context Store — Design detalhado

### Visão geral

Um schema `context` no PostgreSQL que acumula conhecimento de domínio e integrações ao
longo do tempo. Cada etapa do pipeline lê e escreve nesse store — ele é o componente
transversal que conecta ingestão, integração e transformação.

```
ingestão ──writes──▶ context.column_annotations
                     context.table_profiles
                            │
                     (lido por)
                            ▼
integration gateway ──writes──▶ context.integration_discoveries
                                context.domain_contexts
                            │
                     (lido por)
                            ▼
              ContextResolver ──▶ DbtTaskGroup (--select)
```

---

### Schema completo

```sql
-- 1. Grupos de domínio persistidos (substitui o dict Python hardcoded)
CREATE TABLE context.domain_contexts (
    domain_name     TEXT PRIMARY KEY,
    semantic_groups JSONB NOT NULL,  -- {"empenho": ["nr_empenho", ...]}
    key_patterns    JSONB,
    source          TEXT NOT NULL,   -- "builtin" | "user-defined"
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- 2. Anotação de colunas com domain_group (escrita na ingestão)
CREATE TABLE context.column_annotations (
    table_name    TEXT NOT NULL,
    column_name   TEXT NOT NULL,
    domain_group  TEXT,
    semantic_tags TEXT[],
    detected_at   TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (table_name, column_name)
);

-- 3. Perfil analítico de tabelas (escrita pós-stage_silver, task separada)
CREATE TABLE context.table_profiles (
    table_name              TEXT PRIMARY KEY,
    row_count               INTEGER,
    exercicio_distribution  JSONB,
    cardinality_per_col     JSONB,
    quality_ok              BOOLEAN,
    profiled_at             TIMESTAMPTZ DEFAULT now()
    -- NÃO duplica catalog.ingested_tables — foco em semântica, não rastreabilidade
);

-- 4. Integrações descobertas (escrita pelo IntegrationAgent via bridge.py)
CREATE TABLE context.integration_discoveries (
    table_a              TEXT NOT NULL,
    column_a             TEXT NOT NULL,
    table_b              TEXT NOT NULL,
    column_b             TEXT NOT NULL,
    confidence           FLOAT NOT NULL,
    discovery_method     TEXT,           -- "semantic" | "content" | "domain_group"
    justification        TEXT,           -- reasoning do LLM
    evidence_for         JSONB,
    evidence_against     JSONB,
    required_transforms  JSONB,
    is_validated         BOOLEAN DEFAULT NULL,  -- NULL=auto, TRUE=confirmado, FALSE=rejeitado
    discovered_at        TIMESTAMPTZ DEFAULT now(),
    last_confirmed_at    TIMESTAMPTZ,
    PRIMARY KEY (table_a, column_a, table_b, column_b)
);
```

---

### Pontos de escrita

| Evento | Task | Tabelas escritas |
|---|---|---|
| `stage_silver` conclui | `annotate_context` (nova task no DAG) | `column_annotations` |
| `profile_table` conclui | mesma task `profile_table` | `table_profiles` |
| `IntegrationAgent.save()` | `bridge.py` (já existe) | `integration_discoveries` com todos os campos |
| `/definir-contexto` | script CLI | `domain_contexts` (persiste domínios customizados) |

**DAG de ingestão revisado:**
```
extract → write_bronze → stage_silver → annotate_context
                                    ↘ profile_table
```

---

### `find_domain_group` conectado ao banco

O `find_domain_group` passa a consultar `context.domain_contexts` antes do fallback Python:

```python
def find_domain_group(col_name: str, db_conn=None) -> str | None:
    if db_conn:
        # consulta o store primeiro
        groups = _load_from_store(db_conn)
    else:
        groups = DOMAIN_SEMANTIC_GROUPS  # fallback builtin
    # mesma lógica de matching sobre `groups`
```

Isso torna os grupos de domínio extensíveis sem editar código — basta inserir em
`context.domain_contexts`.

---

### `ContextResolver` — mediador entre Context Store e dbt

Componente Python que roda antes do `DbtTaskGroup` e decide o `--select`:

```python
class ContextResolver:
    def __init__(self, db_conn):
        self.db = db_conn

    def get_select_for_package(self, package_name: str) -> str:
        discoveries = self._query_confirmed_discoveries(package_name)
        if not discoveries:
            return "models/bronze/"      # sem integração confirmada: só bronze
        return "models/"                 # há integração: roda bronze+silver+gold
    
    def _query_confirmed_discoveries(self, package_name: str):
        return self.db.execute("""
            SELECT * FROM context.integration_discoveries
            WHERE (table_a LIKE %s OR table_b LIKE %s)
              AND (is_validated IS NULL OR is_validated = TRUE)
              AND confidence >= 0.7
        """, (f"{package_name}%", f"{package_name}%")).fetchall()
```

---

### Separação catalog vs context

| Schema | Responsabilidade | Quem lê |
|---|---|---|
| `catalog.ingested_tables` | Rastreabilidade operacional — quando, quantas linhas, qualidade OK/NOK | Airflow, Integration Gateway (para descobrir pares) |
| `context.table_profiles` | Perfil semântico — cardinalidade, exercício distribution | `mapear-integracoes`, `ContextResolver` |
| `context.column_annotations` | Domain groups por coluna | `mapear-integracoes`, `find_domain_group` |
| `context.integration_discoveries` | Chaves de integração com evidências e confiança | `ContextResolver`, dbt (via mediador) |
| `context.domain_contexts` | Vocabulários de domínio persistidos | `find_domain_group`, `/definir-contexto` |

---

### Gestão do schema `context`

O schema `context` é criado e versionado pelo **dbt** — não por código runtime:

```sql
-- transformation/models/context/schema_init.sql (dbt seed ou hook)
CREATE SCHEMA IF NOT EXISTS context;
```

Migrations de novas colunas passam por PR de model dbt — rastreáveis e reversíveis.
