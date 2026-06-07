# ADR 0004 — Integration Gateway como ponte entre ingestion e IntegrationAgent

**Status:** Proposto

## Contexto

O `data-application-gov-hub` ingere dados de 14+ sistemas governamentais em schemas PostgreSQL separados (`siafi`, `compras_gov`, `siape`, etc.). O projeto `tcc/gov-hub/integration/` contém um IntegrationAgent capaz de identificar automaticamente chaves de integração entre duas tabelas usando análise semântica, estatística e raciocínio LLM.

Os dois projetos não se comunicam hoje. A identificação de qual campo do SIAFI conecta com qual campo do TransfereGov é feita manualmente, com alto custo de exploração e risco de erro.

## Decisão

Criar um Integration Gateway que serve como camada de integração entre o pipeline de ingestão e o IntegrationAgent:

1. O **Table Catalog** (`catalog.ingested_tables` no PostgreSQL) registra cada tabela carregada com sucesso no silver.
2. O **Integration Gateway** (`bridge/integration_bridge.py`) é acionado via DAG Airflow separada (`integration_bridge_dag`), recebendo `table_a` e `table_b` como parâmetros.
3. O gateway consulta o Catalog para confirmar disponibilidade e qualidade das tabelas, carrega os DataFrames do PostgreSQL e chama `IntegrationAgent.run()`.
4. O resultado é persistido em `output/identificar_chave_<a>__<b>.json`.

A DAG pode ser disparada manualmente por um operador ou automaticamente por um sensor que monitora o Catalog em busca de pares novos com alta afinidade semântica.

## Alternativa rejeitada

Integrar o IntegrationAgent diretamente dentro dos DAGs de ingestão existentes, chamando-o ao final de cada carga. Rejeitado porque: (1) acopla lógica de integração à lógica de ingestão de cada fonte; (2) identificação de chave faz sentido entre pares de tabelas — não faz sentido rodar a cada carga individual; (3) aumenta o tempo de execução dos DAGs de ingestão com lógica não relacionada.

## Consequências

- O Table Catalog precisa ser implementado antes do Gateway funcionar de forma automática. No curto prazo, o Gateway pode ser disparado manualmente sem o Catalog.
- O IntegrationAgent do `tcc/gov-hub/integration/` precisa ter acesso ao PostgreSQL do `data-application-gov-hub` — mesma rede Docker ou via variáveis de ambiente apontando para o mesmo banco.
- O resultado do IntegrationAgent (JSON com a Integration Key recomendada) alimenta a construção de modelos DBT de join entre schemas — próximo passo natural após a identificação da chave.
