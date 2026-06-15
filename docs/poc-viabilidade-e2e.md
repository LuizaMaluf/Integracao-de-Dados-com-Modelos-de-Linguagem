# PoC de Viabilidade — Arquitetura Gov-Hub ponta a ponta

**Data:** 2026-06-15
**Objetivo:** verificar se a arquitetura de três camadas (ingestão config-driven → transformação dbt → integração semântica via LLM) é viável na prática, executando o processo completo com dados governamentais reais.

**Método:** rodar o pipeline de verdade — Airflow + MinIO + DuckDB + PostgreSQL + dbt + Decision Layer LLM — contra APIs públicas reais (IBGE), atravessando cada camada e registrando onde a arquitetura se sustenta e onde apresenta lacunas.

---

## Resumo executivo

A arquitetura **é viável**, com uma ressalva central: a promessa *"adicionar uma fonte = só um YAML"* vale plenamente na **camada de ingestão**, mas **não se estende** às camadas de transformação e integração, que ainda exigem trabalho manual por fonte. O raciocínio semântico via LLM (a tese principal) funcionou e superou a análise estatística num caso real.

A PoC também revelou **quatro bugs** que impediam o pipeline de rodar ponta a ponta — todos do tipo "a arquitetura foi projetada mas nunca executada de fato".

---

## O que foi provado (ao vivo, dados reais)

### Camada 1 — Ingestão config-driven ✅

- Criados **3 YAMLs novos** (IBGE municípios, IBGE estados, BCB PTAX) e **zero linhas de código de DAG**.
- O Airflow real gerou automaticamente **5 DAGs `ingest_api_*`**, um por YAML, a partir de um único `api_dag.py`.
- O DAG do IBGE municípios executou de ponta a ponta: **API → MinIO (bronze, parquet 170 KiB) → DuckDB (silver, 5.571 linhas reais)**.
- O `ApiExtractor` genérico cobriu **2 famílias de API com dado real** (array cru — IBGE; OData-wrapped — BCB) apenas por configuração. Uma terceira família (offset/PostgREST) foi implementada no extractor e validada por teste com mock.

**Custo de uma família de API nova (offset/PostgREST, adicionada ao extractor):** ~14 linhas na classe base genérica — não por fonte. Toda fonte futura da mesma família é só YAML.

### Camada 3 — Integração semântica via LLM ✅

Par integrado: `ibge_municipios` × `ibge_estados` (dados que atravessaram todo o pipeline).

A Decision Layer (rodada via subscrição Claude Code) **identificou a chave correta** `municipios.uf_id ↔ estados.id` e demonstrou raciocínio de domínio que a estatística não alcançou:

- **Superou um falso negativo:** todos os candidatos tinham `match_rate 0%`. O LLM diagnosticou a causa — incompatibilidade de tipo (`uf_id` float64 `35.0` vs `id` int64 `35`) — e recomendou o CAST.
- **Rejeitou uma armadilha:** `municipio_id↔id` tinha score numérico maior, mas o LLM reconheceu tratar-se de uma *Derived Key* (prefixo de 2 dígitos do código IBGE), redundante para a junção.

Esta é a evidência mais forte da tese: **o raciocínio semântico acertou onde a heurística estatística falhou completamente.**

---

## As costuras entre camadas (lacunas de arquitetura)

### Costura A — Ingestão → Transformação: storages incompatíveis 🔴

A camada 1 grava o silver em **DuckDB** (arquivo); o dbt lê de **PostgreSQL**. **Não existe ponte no código** entre os dois. Além disso, o `docker-compose` não sobe nenhum Postgres analítico — só o de metadados do Airflow.

Para atravessar, foi necessário **escrever um script ad-hoc** (ler DuckDB → achatar structs → escrever Postgres) e subir um Postgres manualmente. As 5.571 linhas chegaram ao `silver.ibge_municipios`.

### Costura B — Transformação não é config-driven 🔴 (achado central)

O dbt está **hardcoded em fontes SIAFI/Transfere/Compras**: os 9 sources e os models são escritos à mão. O dado do IBGE estava no Postgres, mas o dbt **não tinha como saber que ele existia**.

Para o IBGE virar Bronze foi preciso escrever **à mão**: +6 linhas em `sources.yml` e um model `.sql`. O `dbt run` então funcionou (`bronze.ibge_municipios`, `SELECT 5571`).

**Conclusão:** a promessa "sem código novo" da ingestão **quebra na transformação**. Cada fonte nova exige SQL manual.

### Costura C — Integração lê CSV, não o banco 🟡

A camada 3 consome **CSV**, enquanto o dado está em DuckDB/Postgres. Foi necessário exportar as tabelas para CSV antes de integrar.

---

## Bugs encontrados e corrigidos

| # | Bug | Sintoma | Correção |
|---|-----|---------|----------|
| 1 | Ciclo de YAML anchor no `docker-compose.yml` | Compose v5 recusa subir | anchor próprio para o bloco `environment` |
| 2 | DAGs sem `start_date` | `ValueError: DAG is missing the start_date` — nenhum `ingest_api_*` carregava | `start_date=datetime(2024,1,1)` |
| 3 | Permissão do volume DuckDB | `IOException: Permission denied` no silver | `chown airflow` em `/opt/airflow/data` |
| 4 | `_PIP_ADDITIONAL_REQUIREMENTS` pesado | init travava 27 min em backtracking (`unstructured[pdf]`) | override com deps enxutas para a PoC |

Achado menor: as tasks `annotate_context`/`profile_table` falham porque o diretório `context/` não está montado nos volumes do compose.

---

## Veredito de viabilidade

| Camada | Viável? | Config-driven real? |
|---|---|---|
| 1 — Ingestão | ✅ Sim, validada ao vivo | ✅ Sim (só YAML) |
| 2 — Transformação (dbt) | ✅ Funciona | ❌ Não (SQL manual por fonte) |
| 3 — Integração (LLM) | ✅ Sim, supera a estatística | n/a (lê CSV) |
| Costuras entre camadas | ⚠️ Exigem pontes manuais | — |

**A arquitetura é viável para a realidade do TCC.** A tese de portabilidade semântica se sustenta na ingestão e na integração. As lacunas (costuras A/B/C) são reais mas bem delimitadas e representam trabalho futuro claro, não falhas conceituais — exatamente o tipo de fronteira que um TCC honesto deve mapear.

---

## Artefatos da PoC

**Logs de evidência** (saída real de comando, capturada do sistema vivo) — ver [poc-artefatos/](poc-artefatos/):

| # | Log | Embasamento |
|---|-----|-------------|
| 01 | DAGs config-driven | 5 DAGs `ingest_api_*`, 1 por YAML |
| 02 | Execução do DAG IBGE | tasks extract→bronze→silver success |
| 03 | Bronze + Silver | parquet 170KiB + 5.571 linhas reais |
| 04 | dbt run | `INSERT 0 5571`, Completed successfully |
| 05 | Decision Layer LLM | `uf_id↔id` escolhido com match 0% |
| 07 | Bugs corrigidos | erros + estado pós-fix |

**Código e configs alterados:**
- Configs novos: `ingestion/configs/{ibge_municipios,ibge_estados,bcb_ptax_moedas}.yaml`
- Extractor estendido (array cru + OData + offset/PostgREST): `ingestion/extractors/api_extractor.py`
- Reasoner com backend selecionável (API ou CLI/subscrição): `integration/src/agent/llm_reasoner.py`
- Fix do ciclo YAML + override de deps: `ingestion/docker-compose.yml`, `ingestion/docker-compose.override.yml`
- `start_date` nas DAGs: `ingestion/dags/api_dag.py`
- Resultado da integração: `integration/output/poc_e2e_ibge.json`
