# ADR 0008 — Transformation DAG Factory config-driven com data-aware scheduling

**Status:** Aceito

## Contexto

O `transformation_dag.py` existente era manual: executava todos os modelos dbt sem discriminação de pacote ou de estado de integração. A transformação disparava em cron fixo, independente de o silver layer ter sido atualizado. O `--select` era estático, rodando modelos gold mesmo quando nenhuma integração havia sido confirmada no Context Store. Adicionar um novo pacote dbt exigia editar código Python diretamente.

## Decisão

Substituir `transformation_dag.py` por `transformation_dag_factory.py`: uma factory que lê os Source Registry YAMLs, extrai as declarações `dbt_packages` de cada fonte, e gera um DAG `transform_<pkg>` por pacote dbt.

Dois mecanismos-chave:

**Data-aware scheduling:** cada DAG `transform_<pkg>` é agendado via `Dataset` produzido pela ingestão correspondente — só dispara após atualização real do silver layer, sem cron fixo.

**`--select` dinâmico via ContextResolver:** o caminho dbt é resolvido em runtime consultando `context.integration_discoveries`. Sem integração confirmada → `models/bronze/`. Com integração confirmada (confiança ≥ 0.7) → `models/` (pipeline completo).

```python
# Source Registry YAML — declaração do pacote dbt
dbt_packages:
  - name: siafi
    select: models/

# DAG gerado automaticamente
@dag(schedule=[Dataset("silver://siafi_notas_empenho")])
def transform_siafi():
    dbt_select = get_dbt_select("siafi", resolver)   # "models/" ou "models/bronze/"
    DbtTaskGroup(..., operator_args={"select": dbt_select})
```

## Alternativa rejeitada

Manter `transformation_dag.py` com cron fixo e `--select` estático. Rejeitado porque: (1) cron fixo gera execuções em vazio quando o silver não foi atualizado; (2) `--select models/` fixo roda modelos gold sem joins definidos; (3) novos pacotes dbt exigem PR de código Python, quebrando o contrato config-driven.

## Consequências

- Novos pacotes dbt entram via campo `dbt_packages` no YAML da fonte — sem PR de código.
- Transformação só dispara após ingestão real (data-aware scheduling), eliminando runs em vazio.
- `--select` adapta-se ao estado do Context Store: evolui automaticamente conforme integrações são confirmadas.
- `ContextResolver` com `store=None` retorna `models/bronze/` como fallback seguro em dev e CI sem banco de contexto.
- Falha do `ContextResolver` não bloqueia a transformação: o fallback garante execução mínima (bronze).
