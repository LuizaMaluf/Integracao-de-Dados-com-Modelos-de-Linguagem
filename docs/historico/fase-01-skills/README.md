# Fase 01 — Integration Pipeline como skills do Claude Code

Primeiro ciclo de construção do TCC (Design Science Research). Antes do pacote `govhub.integration` ter uma Decision Layer própria, a descoberta de chaves era feita por oito skills do Claude Code, encadeadas por arquivo:

| Skill | Papel na Fase 01 | O que virou |
| --- | --- | --- |
| `definir-contexto` | Gera o Domain Context (grupos de colunas, padrões de identificador) | `govhub/integration/config/domain.py` |
| `analisar-tabela` | Perfil de cada tabela | `analyzers/structural.py`, `transformers/pattern_detector.py` |
| `comparar-colunas` | Evidence Layer: evidências por par de colunas | `agent/candidate_generator.py` |
| `comparar-dados` | Content Evidence Layer: sinais pelos valores, sem usar o nome | `analyzers/content_analyzer.py` |
| `identificar-chave` | Decision Layer: o Claude escolhe a Integration Key | `agent/orchestrator.py`, `agent/llm_reasoner.py` |
| `gerar-relatorio` | Relatório HTML da decisão | — |
| `integrar-bases` | Orquestra o pipeline completo para um par de tabelas | `govhub` (CLI) |
| `mapear-integracoes` | Varre várias tabelas em busca de pares integráveis | — |

Os PRDs desta fase estão aqui também: [`prd-pipeline-orchestration.md`](prd-pipeline-orchestration.md) e [`prd-comparar-dados.md`](prd-comparar-dados.md).

## Por que foram desativadas

Nas skills, quem raciocina e decide a chave é o próprio agente no chat, em texto livre: o LLM *é* o pipeline. A tese do TCC (ADR 0011, a partir do artigo-base) é a oposta: o LLM só decide dentro da Decision Layer, com saída tipada e validada, e todo artefato executado sai de um estágio determinístico. Mantidas ativas em `.claude/skills/`, elas seriam disparadas automaticamente pelo Claude Code e poderiam contornar a Decision Layer durante os incrementos avaliados na QP5.

As skills foram movidas para cá em 2026-10-03 (`docs/specs/limpeza-escopo.md`), sem edição. Elas citam módulos removidos na mesma limpeza (`context_loader`, `context_validator`, `exercicio_profiler`); o código da época está no commit `8eac61d`.
