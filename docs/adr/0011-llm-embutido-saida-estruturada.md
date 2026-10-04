# ADR 0011 — LLM embutido com saída estruturada e estágio determinístico

**Status:** Proposto

## Contexto

A Decision Layer (`govhub.integration.agent.llm_reasoner`) chama o LLM com um prompt livre e extrai o JSON da resposta procurando o primeiro `{` e o último `}`. Quando o parsing falha, devolve `{"raw_response": ..., "error": ...}` e o pipeline segue sem decisão. Não há validação do esquema da saída, nova tentativa, registro do raciocínio nem troca de modelo por configuração além de `MODEL_NAME`.

O artigo-base do TCC (SPAPI-Tester, `docs/tcc/artigo-base.md`) resolve o mesmo tipo de problema — o "de-para" entre fontes em silos — com um padrão que separa o que exige julgamento do que é mecânico: módulos estruturados → LLM → módulos estruturados.

## Decisão

1. **O LLM só decide o de-para.** Recebe as evidências já coletadas (Evidence Layer e Content Evidence Layer) e o esquema completo das duas tabelas, com perfil e amostra de valores de cada coluna, e devolve um **dicionário de mapeamento** tipado: Integration Key (ou Abstenção), transformações necessárias, categoria de atrito resolvida, confiança e justificativa. Os Candidate Keys ordenam as opções, mas não limitam a resposta: o LLM pode propor uma chave fora da lista, inclusive composta ou derivada, e o estágio determinístico a valida executando o join. Como no artigo-base, o estágio anterior ao LLM reúne a informação dos silos; não filtra as respostas possíveis.
2. **Saída tipada com autocorreção.** A chamada passa a usar DSPy: assinatura com tipos de entrada e esquema de saída, `ChainOfThought` para registrar o raciocínio, e nova chamada com a mensagem de erro quando a validação da saída falhar (limite de tentativas configurável).
3. **O LLM nunca escreve SQL.** Um estágio determinístico gera, a partir do dicionário, o model dbt de join e seus testes via templates Jinja — o mesmo padrão do `dbt_source_generator` (ADR 0010). As transformações do dicionário vêm de um **Catálogo de Transformações** fechado: cada lado da chave é uma sequência curta (até 3) de operações tipadas — `converter_tipo`, `normalizar_texto`, `remover_mascara`, `preencher_zeros`, `trecho`, `concatenar`, `mapear_valores`, `converter_data` —, cada uma com um template SQL fixo e teste unitário. Operação fora do catálogo reprova a validação e dispara a autocorreção; se o LLM não conseguir expressar a chave no catálogo, a saída é Abstenção com esse motivo, contada à parte na avaliação. O catálogo é versionado e congelado junto com o ground truth.
4. **Modelo trocado por configuração.** Provedor e modelo (proprietário ou de pesos abertos rodando localmente) vêm do `.env`, sem mudança de código, para permitir a comparação da QP2.
5. **Raciocínio e custo registrados.** Cada decisão guarda o raciocínio, o modelo, a versão, os tokens e a latência junto do resultado.

## Alternativas rejeitadas

- **Manter o prompt livre + extração de JSON:** falha silenciosa e resultado não reproduzível; sem base para avaliar por modelo.
- **LLM gerando o SQL do join diretamente:** mistura julgamento com código executado; o artigo-base mostra que manter o LLM fora do artefato executado dá previsibilidade e rastreabilidade. A avaliação mede essa alternativa como baseline (B4).
- **Transformação em texto livre no dicionário:** obrigaria o estágio Jinja a interpretar linguagem natural, ou faria o LLM escrever SQL por outra porta.
- **LLM só reordenando os Candidate Keys:** chaves compostas, derivadas ou aninhadas nunca entram na lista, então o acerto nessas categorias ficaria limitado pelo gerador de candidatos e não mediria o LLM.
- **Dicionário de sinônimos determinístico no lugar do LLM:** não cobre abreviações, equivalências lógicas e Derived Keys sem manutenção contínua (mesma conclusão do artigo-base). O Domain Context atual é um dicionário desse tipo; a avaliação mede essa alternativa numa ablação 2 × 2 (com e sem LLM × com e sem Domain Context), em vez de só citá-la.

## Consequências

- Nova dependência (`dspy`) no extra de integração; a Decision Layer ganha um esquema de saída versionado.
- A avaliação da QP1–QP2 passa a comparar modelos com o mesmo código.
- O caminho sem LLM (`--no-llm`) continua existindo como baseline.
- Implementação pendente: ver "Lacunas e plano de trabalho" em `docs/tcc/proposta.md`.
