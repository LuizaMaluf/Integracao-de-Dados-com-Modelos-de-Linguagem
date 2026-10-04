# Limpeza do repositório para o escopo do TCC

**Status:** Implementada
**ADR relacionada:** 0011 (escopo do LLM embutido); descontinua as ADRs 0001–0010

## Problema

O repositório acumula a pilha de ingestão config-driven (Airflow, MinIO, DuckDB, costuras A/B), exemplos sintéticos da PoC, ingestão de PDF, o Context Store e as skills da Fase 01, que ainda estão ativas. Desde a revisão da proposta de 2026-10-03, o TCC trata só da descoberta de chaves com LLM embutido e do SDD; a ingestão das bases é feita pelo GovHub (`data-application-gov-hub`), e este repositório lê do PostgreSQL do GovHub ou de snapshots exportados de lá. O excesso confunde quem lê, mantém dependências pesadas e deixa ativas skills que contornam a Decision Layer tipada.

## Escopo

- **Dentro:**
  1. **Pilha de ingestão:** remover `airflow/`, `src/govhub/ingestion/`, `src/govhub/sync/`, `tests/ingestion/` e `tests/sync/`; no `docker-compose.yml`, manter só o serviço `postgres`; no `Makefile`, remover os alvos de Airflow, MinIO e `dbt-generate`; no `pyproject.toml`, trocar o extra `ingestion` por um extra `postgres` (só `sqlalchemy` e `psycopg2-binary`), tirar `airflow` do `pythonpath` e o marker `e2e`; no `.env.example`, remover MinIO, DuckDB e `ANTHROPIC_MODEL`.
  2. **Context Store:** remover `src/govhub/integration/store/`, `tests/integration/test_context_store.py`, o `package-data` do `schema.sql`, o parâmetro `store` de `find_domain_group` e os dois testes que o usam.
  3. **Models dbt de exemplo:** remover `dbt/models/bronze/`, `silver/` e `gold/` e as configurações dessas camadas no `dbt_project.yml`. Fica o esqueleto do projeto dbt, onde o estágio Jinja → dbt vai gerar os models de join.
  4. **Skills da Fase 01:** mover as 8 skills de integração (`analisar-tabela`, `comparar-colunas`, `comparar-dados`, `definir-contexto`, `gerar-relatorio`, `identificar-chave`, `integrar-bases`, `mapear-integracoes` — com os evals) e os PRDs `prd-comparar-dados.md` e `prd-pipeline-orchestration.md` para `docs/historico/fase-01-skills/`, com um README que explica o papel delas como primeiro ciclo da DSR e por que foram desativadas (ADR 0011). Remover `context_validator.py`, `context_loader.py` e `exercicio_profiler.py`, usados só pelas skills. A skill `doc-tcc` continua ativa, sem referência a `docs/architecture/`.
  5. **Documentação obsoleta:** remover `docs/ingestion.md`, `docs/architecture/`, `docs/specs/possivel-solucao-dbt.md`, `docs/tcc/artefatos.html` e `docs/tcc/assets/artefato1.png`, e o link para `artefatos.html` em `docs/tcc/index.html`. Mover `docs/specs/costuras-e2e.md` para `docs/historico/`.
  6. **ADRs 0001–0010:** status passa a "Descontinuada (2026-10-03) — fora do escopo do TCC; ver `docs/specs/limpeza-escopo.md`". Nenhuma ADR é apagada.
  7. **Agentes:** apagar `.agents/` (cópia mecânica das skills, fora do git); `AGENTS.md` vira link simbólico para `CLAUDE.md` e passa a ser versionado.
  8. **Loader e testes do PostgreSQL:** os testes de `PostgresLoader` e da CLI deixam de depender do `silver_sync` e carregam os dados com `pandas.DataFrame.to_sql`.
  9. **Documentos ativos:** README enxuto (o que é o TCC, estrutura, comandos); `CLAUDE.md` (Estrutura e Comandos); `CONTEXT.md` (termos que citam skills: Integration Pipeline, Domain Context, Context Coverage, Evidence Layer, Content Evidence Layer, Decision Layer); `docs/tcc/proposta.md` ("Fora do foco", lacunas, capítulos 5 e 6).
  10. **Lint (incluído depois da aprovação):** corrigir os 30 erros de estilo do ruff que restaram no código mantido (ordem de imports, imports sem uso, linhas longas), sem mudar comportamento — o CA2 pressupunha um lint que já passava, e havia 78 erros antes da limpeza.
- **Fora:**
  - `poc/` (local, fora do git) e a branch `gh-pages`.
  - Reescrever `docs/tcc/index.html` além do link morto.
  - Qualquer mudança de comportamento na Decision Layer.
  - Script de snapshot das bases do GovHub (próximo incremento, com spec própria).

## Contrato

- Pacote após a limpeza: `govhub.integration.{agent,analyzers,config,loaders,transformers}`, `govhub.llm`, `govhub.postgres` e `govhub.cli`.
- A CLI `govhub --table-a … --table-b … [--no-llm]` continua aceitando CSV e `pg://schema.tabela`.
- `pip install -e ".[postgres,dev]"` instala tudo o que os testes precisam.
- `docker compose up -d` sobe só o PostgreSQL local (testes `pg` e dbt).

## Critérios de aceite

- [x] CA1 — A suíte de testes passa; os testes `pg` são pulados sem banco · verificado por `make test`
- [x] CA2 — O lint passa · verificado por `make lint`
- [x] CA3 — Nenhuma referência a módulo removido no código, na configuração e nas instruções ativas · verificado por `grep -rnE "govhub\.(ingestion|sync)|context_store|ContextStore|context_validator|context_loader|exercicio_profiler|silver_sync" src tests Makefile pyproject.toml docker-compose.yml CLAUDE.md .claude` sem resultado
- [x] CA4 — A CLI integra dois CSV sem LLM e grava o JSON · verificado por `govhub --table-a <a.csv> --table-b <b.csv> --no-llm --output <saida.json>` com dois CSV de teste
- [x] CA5 — `.claude/skills/` contém só `doc-tcc`; `docs/historico/fase-01-skills/` contém as 8 skills, os 2 PRDs e o README · verificado por `ls`
- [x] CA6 — O compose só tem o PostgreSQL · verificado por `docker compose config --services` = `postgres`
- [x] CA7 — ADRs 0001–0010 com status Descontinuada e a 0011 inalterada · verificado por `grep -L "Descontinuada" docs/adr/00{01..10}-*.md` sem resultado
- [x] CA8 — `AGENTS.md` é link para `CLAUDE.md` e `.agents/` não existe · verificado por `test -L AGENTS.md && test ! -e .agents`

**Testes-oráculo:** não se aplicam — incremento de manutenção, anterior ao protocolo da QP5 e fora da comparação pareada; os critérios são verificados pelos comandos acima.

## Plano

1. Commit separado, antes desta spec, com as mudanças de metodologia da revisão de 2026-10-03.
2. Branch `limpeza-escopo`.
3. `git mv` das skills, dos PRDs e da `costuras-e2e.md` para `docs/historico/`; README do histórico.
4. `git rm` da pilha de ingestão, do Context Store, dos models dbt de exemplo e da documentação obsoleta; apagar `.agents/`; criar o link `AGENTS.md`.
5. Ajustes de código e configuração: `find_domain_group` sem `store`; testes do PostgreSQL com `to_sql`; `pyproject.toml`, `Makefile`, `docker-compose.yml`, `.env.example` e `dbt_project.yml`.
6. Documentos: status das ADRs, README, `CLAUDE.md`, `CONTEXT.md`, `proposta.md` e a skill `doc-tcc`.
7. Reinstalar o pacote e verificar CA1–CA8.

## Registro para a QP5 (preencher ao final)

Incremento avaliado em comparação pareada? Não — manutenção, anterior ao protocolo da QP5.

| Métrica | Braço com spec | Braço sem spec |
| --- | --- | --- |
| Testes-oráculo passando na primeira entrega | — | — |
| Testes-oráculo passando ao final | — | — |
| Iterações até a entrega final | 2 (CA2 falhou na primeira verificação) | — |
| Intervenções (registradas literalmente abaixo) | 0 | — |
| Tokens | não medido | — |
| Tempo da autora (escrita da spec + acompanhamento) | não medido | — |
| Mudanças na spec depois de aprovada | 1 (item 10 do escopo: correção do lint) | — |
| Divergências spec × código encontradas | 1: o CA2 supunha lint passando; havia 78 erros antes da limpeza | — |
| Observações | CA1–CA8 verificados em 2026-10-03: 34 testes passando e 2 `pg` pulados sem banco; os 2 `pg` também passaram contra um PostgreSQL 17 descartável. O `.venv` do repositório está quebrado (aponta para o caminho antigo do repo); a verificação usou um ambiente novo. O prompt do LLM ficou idêntico após quebrar a linha longa. A ADR 0011 manteve o status; o texto só trocou a referência ao `dbt_source_generator` removido. | |

Intervenções, na ordem:

Nenhuma durante a implementação. As decisões de escopo (remover a pilha de ingestão, arquivar as skills, link do `AGENTS.md`) foram tomadas antes da spec ser aprovada.
