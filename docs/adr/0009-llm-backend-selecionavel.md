# ADR 0009 — Backend de inferência LLM selecionável (API ou CLI de subscrição)

**Status:** Aceito

## Contexto

A Decision Layer da camada de integração (`integration/src/agent/llm_reasoner.py`) chamava o SDK da API Anthropic (`client.messages.create`), que cobra créditos de API pré-pagos. Durante a PoC de viabilidade ponta a ponta, a conta de API estava sem saldo (erro 400 "credit balance too low"), embora houvesse uma assinatura Claude Code (autenticada via OAuth) disponível na máquina. A assinatura autentica o CLI `claude`, não o SDK de API — os dois mecanismos de cobrança são separados.

## Decisão

Tornar o backend de inferência selecionável via variável de ambiente `LLM_BACKEND`:
- `api` (default): mantém o SDK Anthropic, cobrando créditos de API.
- `cli`: chama o binário `claude -p` (modo headless) via `subprocess`, usando a assinatura Claude Code.

O prompt, o parsing do JSON de resposta e o formato de saída permanecem idênticos entre os dois backends — só a chamada de inferência muda.

## Alternativa rejeitada

Migrar permanentemente para o CLI e remover o SDK de API. Rejeitada porque o SDK é o caminho padrão para execução headless/CI (onde não há assinatura interativa), e o CLI depende de login OAuth presente na máquina. Manter ambos preserva os dois cenários.

## Consequências

- A integração roda sem créditos de API quando há assinatura Claude Code disponível — útil para desenvolvimento e para a realidade de recursos do TCC.
- O backend `cli` acopla a execução à presença do binário `claude` autenticado; falha com `RuntimeError` se ausente.
- A latência do backend `cli` é maior (overhead de processo) e não é adequado para alto volume.
