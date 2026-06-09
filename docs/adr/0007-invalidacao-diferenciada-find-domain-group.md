# ADR 0007 — Invalidação diferenciada + `find_domain_group` conectado ao banco

**Status:** Aceito

## Contexto

Re-ingestão de uma fonte pode deixar `column_annotations` desatualizadas se o schema da tabela mudou. Discoveries com confiança alta mas semanticamente incorretas não tinham mecanismo de correção sem apagar o registro. `find_domain_group` só conhecia domínios compilados em Python — sem extensibilidade em runtime.

## Decisão

**Invalidação por tipo de tabela:**

| Tabela | Estratégia | Motivo |
|---|---|---|
| `column_annotations` | Upsert simples — estado atual é a verdade | Schema da tabela é determinístico: re-ingestão produz o mesmo resultado |
| `table_profiles` | Upsert simples | Profile reflete o estado atual do dado, não histórico |
| `integration_discoveries` | Upsert com `GREATEST(confidence)` + `is_validated` | Discoveries acumulam — confiança só sobe; override humano via flag |

**`find_domain_group` conectado ao banco:** a função passa a aceitar `store` como parâmetro opcional. Quando fornecido, consulta `context.domain_contexts` primeiro e merge com os grupos builtin Python:

```python
def find_domain_group(col_name: str, store=None) -> str | None:
    if store:
        custom_groups = {g["domain_name"]: g["semantic_groups"]
                         for g in store.get_domain_contexts()}
        groups = {**DOMAIN_SEMANTIC_GROUPS, **custom_groups}
    else:
        groups = DOMAIN_SEMANTIC_GROUPS
    # mesma lógica de matching sobre groups
```

## Alternativa rejeitada

Apagar `integration_discoveries` e reannotar a cada run (invalidação total). Rejeitado porque perde o histórico de quais integrações já foram validadas por analistas, forçando re-validação manual a cada execução.

## Consequências

- Annotations sempre refletem o schema atual — sem drift silencioso.
- Discoveries acumulam sem crescimento descontrolado: mesmo par de colunas só tem uma linha, com a maior confiança já vista.
- Analistas podem rejeitar discoveries incorretas via `is_validated = FALSE` sem apagar o histórico — o registro fica mas é filtrado pelo `ContextResolver`.
- Grupos de domínio são extensíveis via INSERT em `domain_contexts` — sem deploy de código.
- `find_domain_group` sem `store` continua funcionando identicamente (fallback builtin).
