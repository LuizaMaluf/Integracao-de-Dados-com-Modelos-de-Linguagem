# ADR 0005 — Context Store Passivo — quatro tabelas no schema `context`

**Status:** Aceito

## Contexto

O Integration Gateway recalcula tudo do zero a cada run. Os grupos de domínio ficam hardcoded em Python (`DOMAIN_SEMANTIC_GROUPS`) — novos domínios exigem edição de código e deploy. Contextos customizados criados via `/definir-contexto` não sobrevivem entre runs. Não há memória acumulada de descobertas anteriores.

## Decisão

Criar um schema `context` no PostgreSQL com quatro tabelas que acumulam conhecimento de domínio ao longo do tempo:

```sql
context.domain_contexts        -- vocabulários persistidos, substitui o dict Python hardcoded
context.column_annotations     -- domain_group por coluna detectado na ingestão
context.table_profiles         -- perfil analítico (row_count, cardinalidade, qualidade)
context.integration_discoveries -- chaves descobertas com justificativa LLM e flag is_validated
```

O campo `is_validated` em `integration_discoveries` aceita três estados: `NULL` (auto-detectado), `TRUE` (confirmado), `FALSE` (rejeitado por analista) — permitindo override humano sem apagar o histórico.

O schema `context` é gerenciado pelo **dbt** como Schema Registry — não por código runtime. Migrations passam por PR revisável.

## Alternativa rejeitada

Manter os grupos de domínio em dicionário Python e os resultados de integração apenas em arquivos JSON em `output/`. Rejeitado porque: (1) não acumula conhecimento entre runs; (2) novos domínios exigem PR de código; (3) não há mecanismo de override humano sem editar arquivos.

## Consequências

- Novos domínios entram via INSERT em `context.domain_contexts` — sem PR de código.
- O `mapear-integracoes` parte das anotações já acumuladas em `column_annotations`.
- Conhecimento de integração cresce a cada run com `GREATEST(confidence)` no upsert.
- Requer PostgreSQL ativo no ambiente de dev para testes de integração. Testes unitários usam `unittest.mock` — sem dependência de banco.
- `ContextStore` é um cliente de banco sem gestão de conexão: recebe `conn` no `__init__` e não abre/fecha conexões — responsabilidade do chamador.
