# ADR 0006 — Profile em dois momentos + `ContextResolver` como mediador dbt

**Status:** Aceito

## Contexto

Profile completo de tabela (cardinalidade, distribuição de exercício, qualidade) dentro da task `stage_silver` bloqueia a ingestão por vários minutos. O dbt (via `DbtTaskGroup` do cosmos) não consegue consultar `integration_discoveries` diretamente para decidir quais modelos executar — cosmos não tem acesso ao Context Store no momento de geração do `--select`.

## Decisão

**Profile em dois momentos:** separar anotação leve de profile pesado no DAG de ingestão:

```
extract → write_bronze → stage_silver → annotate_context  (leve: domain_group por coluna)
                                    ↘ profile_table        (pesado: cardinalidade, qualidade — paralelo)
```

**`ContextResolver`:** componente Python que roda antes do `DbtTaskGroup` e decide o `--select` dinamicamente consultando `context.integration_discoveries`:

```python
class ContextResolver:
    def get_select(self, package_name: str, min_confidence: float = 0.7) -> str:
        discoveries = self._store.get_discoveries(package_name, min_confidence=min_confidence)
        return "models/" if discoveries else "models/bronze/"
```

Sem integração confirmada → só modelos bronze. Com integração confirmada → pipeline completo (bronze + silver + gold).

## Alternativa rejeitada

Passar `--select` fixo por package no YAML do Source Registry. Rejeitado porque o `--select` correto depende do estado em runtime do Context Store — não é estático no momento de declaração da fonte.

## Consequências

- Falha do `profile_table` não bloqueia a ingestão — as duas tasks são independentes após `stage_silver`.
- O dbt executa apenas os modelos que fazem sentido dado o estado atual das integrações — sem modelos gold rodando sem joins definidos.
- `ContextResolver` com `store=None` retorna `"models/bronze/"` como fallback seguro — funciona em dev sem banco de contexto.
- A lógica de `--select` fica em Python (testável) em vez de diluída em configuração YAML.
