# ADR 0011 — LLM embutido com saída estruturada e estágio determinístico

**Status:** Proposto

## Contexto

A Decision Layer (`govhub.integration.agent.llm_reasoner`) chama o LLM com um prompt livre e extrai o JSON da resposta procurando o primeiro `{` e o último `}`. Quando o parsing falha, devolve `{"raw_response": ..., "error": ...}` e o pipeline segue sem decisão. Não há validação do esquema da saída, nova tentativa, registro do raciocínio nem troca de modelo por configuração além de `MODEL_NAME`.

O artigo-base do TCC (SPAPI-Tester, `docs/tcc/artigo-base.md`) resolve o mesmo tipo de problema — o "de-para" entre fontes em silos — com um padrão que separa o que exige julgamento do que é mecânico: módulos estruturados → LLM → módulos estruturados.

## Decisão

1. **O LLM só decide o de-para.** Recebe as evidências já coletadas (Evidence Layer e Content Evidence Layer) e devolve um **dicionário de mapeamento** tipado: Integration Key, transformações necessárias, categoria de atrito resolvida, confiança e justificativa.
2. **Saída tipada com autocorreção.** A chamada passa a usar DSPy: assinatura com tipos de entrada e esquema de saída, `ChainOfThought` para registrar o raciocínio, e nova chamada com a mensagem de erro quando a validação da saída falhar (limite de tentativas configurável).
3. **O LLM nunca escreve SQL.** Um estágio determinístico gera, a partir do dicionário, o model dbt de join e seus testes via templates Jinja — o mesmo padrão do `dbt_source_generator` (ADR 0010).
4. **Modelo trocado por configuração.** Provedor e modelo (proprietário ou de pesos abertos rodando localmente) vêm do `.env`, sem mudança de código, para permitir a comparação da QP2.
5. **Raciocínio e custo registrados.** Cada decisão guarda o raciocínio, o modelo, a versão, os tokens e a latência junto do resultado.

## Alternativas rejeitadas

- **Manter o prompt livre + extração de JSON:** falha silenciosa e resultado não reproduzível; sem base para avaliar por modelo.
- **LLM gerando o SQL do join diretamente:** mistura julgamento com código executado; o artigo-base mostra que manter o LLM fora do artefato executado dá previsibilidade e rastreabilidade.
- **Dicionário de sinônimos determinístico no lugar do LLM:** não cobre abreviações, equivalências lógicas e Derived Keys sem manutenção contínua (mesma conclusão do artigo-base).

## Consequências

- Nova dependência (`dspy`) no extra de integração; a Decision Layer ganha um esquema de saída versionado.
- A avaliação da QP1–QP2 passa a comparar modelos com o mesmo código.
- O caminho sem LLM (`--no-llm`) continua existindo como baseline.
- Implementação pendente: ver "Lacunas e plano de trabalho" em `docs/tcc/proposta.md`.
