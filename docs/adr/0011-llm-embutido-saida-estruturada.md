# ADR 0011 — LLM embutido com saída estruturada e estágio determinístico

**Status:** Proposto

## Contexto

A Decision Layer (`govhub.integration.agent.llm_reasoner`) chama o LLM com um prompt livre e extrai o JSON da resposta procurando o primeiro `{` e o último `}`. Quando o parsing falha, devolve `{"raw_response": ..., "error": ...}` e o pipeline segue sem decisão. Não há validação do esquema da saída, nova tentativa, registro do raciocínio nem troca de modelo por configuração além de `MODEL_NAME`.

O artigo-base do TCC (SPAPI-Tester, Wang et al., ICSE 2025, pp. 373-384; `docs/tcc/artigo-base.md`) automatiza um processo de teste industrial que dependia do "de-para" entre fontes em silos. Ele mantém as etapas do processo, usa LLM em cada etapa manual discreta, inclusive para gerar os casos de teste, e deixa a renderização e a execução dos testes em código determinístico: módulos estruturados → LLM → módulos estruturados. Este TCC adota o mesmo padrão com uma restrição a mais (bounded agency): aqui o LLM decide uma etapa só, o de-para entre as bases, e artefatos que ele não produziu restringem e checam essa decisão.

## Decisão

1. **O LLM só decide o de-para.** Recebe as evidências já coletadas (Evidence Layer e Content Evidence Layer) e o esquema completo das duas tabelas, com perfil e amostra de valores de cada coluna, e devolve um **dicionário de mapeamento** tipado: Integration Key (ou Abstenção), transformações necessárias, cardinalidade esperada, categoria de atrito resolvida, confiança e justificativa. Os Candidate Keys ordenam as opções, mas não limitam a resposta: o LLM pode propor uma chave fora da lista, inclusive composta ou derivada, e o estágio determinístico a valida executando o join. Como no artigo-base, o estágio anterior ao LLM reúne a informação dos silos; não filtra as respostas possíveis.
2. **Saída tipada, com autocorreção só para saída inválida.** A chamada passa a usar DSPy: assinatura com tipos de entrada, esquema de saída tipado e campo de justificativa curta — o pipeline não depende nem persiste raciocínio livre do modelo. Quando a saída é inválida (fora do esquema ou com operação fora do Catálogo de Transformações), há nova chamada com a mensagem de erro, até um limite de tentativas configurável. Uma decisão válida que falha numa checagem da decisão 5 é rejeitada e o pipeline se abstém, sem nova decisão; a Abstenção registra a checagem que falhou.
3. **O LLM nunca escreve SQL.** Um estágio determinístico gera, a partir do dicionário, o model dbt de join e seus testes via templates Jinja — o mesmo padrão do antigo `dbt_source_generator` (ADR 0010, descontinuada). As transformações do dicionário vêm de um **Catálogo de Transformações** fechado: cada lado da chave é uma sequência curta (até 3) de operações tipadas — `converter_tipo`, `normalizar_texto`, `remover_mascara`, `preencher_zeros`, `trecho`, `concatenar`, `mapear_valores`, `converter_data` e `extrair_identificador(tipo)`, cujo padrão vem do Mapa de Fluxo (ADR 0012) —, cada uma com um template SQL fixo e teste unitário. Parâmetros, limites e o que fica fora do catálogo estão na ADR 0013. Se o LLM não conseguir expressar a chave no catálogo, a saída é Abstenção com esse motivo, contada à parte na avaliação. O catálogo é versionado e congelado junto com o ground truth.
4. **Mapeamento de valores limitado.** A operação `mapear_valores` só pode usar pares presentes no Glossário versionado. O LLM não pode inventar valores, códigos ou equivalências de domínio, nem casar dois valores só porque aparecem nas duas colunas. Cada par aplicado deve ser registrado como evidência no dicionário de mapeamento.
5. **Validação além da execução.** Um join executado é sinal necessário, mas não suficiente: o join pode rodar sobre colunas erradas e correlacionadas. Além dos testes dbt, a validação faz as checagens abaixo, e falhar qualquer uma rejeita a decisão (decisão 2).
   - **Cardinalidade declarada.** A cardinalidade esperada (1:1, N:1, 1:N ou N:N) vem do dicionário de mapeamento e é conferida contra o perfil das colunas (unicidade de cada lado) e contra o join executado (razão de multiplicação de linhas).
   - **Taxa de correspondência nas duas direções.** É medida depois de aplicar o escopo do par às duas tabelas, porque um limiar fixo sobre as tabelas inteiras reprova chaves certas entre bases de cobertura temporal diferente (12% no geral, 96% no mesmo Exercício; ver `CONTEXT.md`). A cardinalidade declarada diz qual direção precisa estar coberta (num N:1, as linhas do lado N precisam achar par no lado 1); a outra direção só tem piso.
   - **Restrição independente de domínio**, quando houver (UF, período ou tipo de entidade). A avaliação relata em quantos pares existe uma restrição desse tipo.
   - **Limiares.** Os valores de cada checagem são calibrados no Conjunto de Desenvolvimento e congelados com o Conjunto de Teste; nenhum é fixado antes disso.
6. **Modelo trocado por configuração.** Provedor e modelo (proprietário ou de pesos abertos rodando localmente) vêm do `.env`, sem mudança de código, para permitir a comparação da QP2.
7. **Justificativa e custo registrados.** Cada decisão guarda a justificativa curta, o modelo, a versão, os tokens e a latência junto do resultado.

## Alternativas rejeitadas

- **Manter o prompt livre + extração de JSON:** falha silenciosa e resultado não reproduzível; sem base para avaliar por modelo.
- **LLM gerando o SQL do join diretamente:** mistura julgamento com código executado; o artigo-base mostra que manter o LLM fora do artefato executado dá previsibilidade e rastreabilidade. A avaliação mede essa alternativa como baseline (B4).
- **Transformação em texto livre no dicionário:** obrigaria o estágio Jinja a interpretar linguagem natural, ou faria o LLM escrever SQL por outra porta.
- **LLM só reordenando os Candidate Keys:** chaves compostas, derivadas ou aninhadas nunca entram na lista, então o acerto nessas categorias ficaria limitado pelo gerador de candidatos e não mediria o LLM.
- **Autocorreção também quando a decisão falha numa checagem:** o LLM poderia tentar chaves até uma passar, e as checagens deixariam de verificar a decisão para virar o critério de uma busca.
- **Dicionário de sinônimos determinístico no lugar do LLM:** não cobre abreviações, equivalências lógicas e Derived Keys sem manutenção contínua (mesma conclusão do artigo-base). O Glossário do Domain Context é um dicionário desse tipo; a avaliação mede essa alternativa na ablação com e sem LLM nos níveis de Domain Context da ADR 0012, em vez de só citá-la.

## Consequências

- Nova dependência (`dspy`) no extra de integração; a Decision Layer ganha um esquema de saída versionado.
- A avaliação da QP1–QP2 passa a comparar modelos com o mesmo código.
- O caminho sem LLM (`--no-llm`) continua existindo como baseline.
- Implementação pendente: ver "Lacunas e plano de trabalho" em `docs/tcc/proposta.md`.
