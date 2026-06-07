# ADR 0001 — Caminho único de notificação via on_failure_callback

**Status:** Aceito

## Contexto

O pipeline tem dois tipos de falha que precisam gerar alerta Telegram: (1) falha de DAG/task por erro de execução, e (2) ingestão que completa com sucesso mas retorna zero registros. O segundo tipo — silencioso por natureza — exige uma task `validate_volume` explícita.

## Decisão

Todo alerta Telegram passa pelo `on_failure_callback` do Airflow. A task `validate_volume` não envia mensagem diretamente — ela levanta uma exceção com texto descritivo (ex: `"validate_volume: 0 registros em finalidades_especiais"`), e o callback formata e envia a mensagem única.

## Alternativa rejeitada

`validate_volume` envia sua própria mensagem Telegram antes de levantar a exceção, e o callback envia uma segunda mensagem de "task falhou". Rejeitado porque gera duas mensagens por evento de volume zero, causando flood no grupo de alertas.

## Consequências

- Um único lugar para mudar o formato da mensagem de alerta.
- O texto da exceção em `validate_volume` precisa ser informativo o suficiente para o operador entender o problema sem ver os logs.
- Falhas que não passam pelo callback (ex: erro de importação do módulo DAG) não geram alerta Telegram.
