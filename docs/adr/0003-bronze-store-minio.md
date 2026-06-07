# ADR 0003 — Adicionar Bronze Store (MinIO) antes do Silver

**Status:** Proposto

## Contexto

O pipeline atual vai direto de API para PostgreSQL. Não existe artefato bruto preservado. Consequências:

- Reprocessar dados históricos exige re-bater nas APIs governamentais, que têm limites de rate, janelas de disponibilidade e podem mudar ou remover dados retroativamente.
- Debugging de problemas de parsing é difícil sem o payload original.
- Não há evidência auditável do dado como veio da fonte.

## Decisão

Adicionar uma camada Bronze imutável antes do Silver: cada execução de extração escreve o payload bruto (JSON da resposta da API) em MinIO antes de qualquer transformação.

- **Ferramenta**: MinIO, S3-compatible, self-hosted, open source (AGPL-3.0).
- **Convenção de path**: `raw/<source_name>/<YYYY-MM-DD>/response.json`
- **Imutabilidade**: uma escrita por execução. Nunca sobrescrito. Reprocessamento lê o bronze e reescreve o silver — sem nova requisição à API.
- **Integração**: MinIO já está no `docker-compose.yml` do projeto irmão (`tcc/gov-hub/ingestion`). A imagem e configuração já existem.

## Alternativa rejeitada

Armazenar o payload bruto como coluna JSONB em um schema `raw` no próprio PostgreSQL. Rejeitado porque: (1) blobs grandes em PostgreSQL degradam performance de vacuum e backup; (2) o PostgreSQL não é um object store — MinIO é a ferramenta certa para artefatos imutáveis; (3) mistura responsabilidades no mesmo banco.

## Consequências

- MinIO é um novo serviço para operar. Adiciona ao `docker-compose.yml`.
- O Bronze Store pode ser adicionado de forma incremental: fontes novas passam pelo bronze; fontes antigas migram gradualmente.
- Se o bronze não for prioridade imediata, o Generic Extractor pode escrever direto no silver sem quebrar a interface — o bronze é inserido como etapa intermediária sem mudar o contrato de entrada/saída.
- Nota sobre licença: em Mai/2025 a MinIO Community Edition removeu o web console. A API S3 (usada pelo código) não foi afetada. Para gestão de buckets sem console, usar `mc` (MinIO Client CLI).
