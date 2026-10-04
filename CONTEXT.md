# Integração Semântica de Bases de Dados

Sistema genérico para identificação de chaves de integração entre tabelas CSV, com suporte a enriquecimento por contexto de domínio. Desenvolvido no contexto do TCC de integração de bases orçamentárias federais brasileiras.

## Language

### Pipeline

**Integration Pipeline**:
A sequência ordenada de cinco etapas que transforma dois arquivos CSV em uma chave de integração documentada: validar-contexto → analisar-tabela → comparar-colunas → identificar-chave → gerar-relatorio.
_Avoid_: fluxo, workflow, processo

**Domain Context**:
Arquivo JSON reutilizável que descreve o vocabulário semântico de um domínio específico — grupos de colunas equivalentes, padrões regex de identificadores e pesos de confiança. Gerado uma vez por domínio pela skill `definir-contexto` e consumido por todas as demais skills. Na avaliação, é congelado junto com o Conjunto de Teste e entra como fator de ablação (com e sem Domain Context).
_Avoid_: configuração, metadados, schema

**Context Coverage**:
Fração das colunas das tabelas de entrada que o Domain Context consegue reconhecer. Usada na validação inicial do pipeline para decidir se o contexto está adequado. Limiar mínimo recomendado: 60%.
_Avoid_: cobertura, aderência

**Evidence Layer**:
Papel da skill `comparar-colunas` no pipeline: coleta dados brutos de compatibilidade (match rate, perfis, transformações necessárias) para cada par de colunas candidato, sem tomar decisões. Produz insumo para a Decision Layer.
_Avoid_: análise, comparação

**Content Evidence Layer**:
Papel da skill `comparar-dados` no pipeline: produz sinais de compatibilidade baseados nos valores reais das colunas — independente de semelhança de nome. Ativada pelo `mapear-integracoes` para pares de tabelas com afinidade < 0.45 que o caminho semântico não conseguiu resolver. Detecta format match (mesmo padrão regex dominante) e sobreposição de valores, incluindo relações de substring que indicam Derived Keys. Produz Candidate Keys com `content_score` para o Decision Layer, sem propor transformações.
_Avoid_: análise de conteúdo, comparação de dados, validação de valores

**Decision Layer**:
Papel da skill `identificar-chave` no pipeline: recebe as evidências da Evidence Layer ou da Content Evidence Layer e o esquema completo das duas tabelas, e decide a melhor chave de integração — um Candidate Key ou outra chave que ela mesma propõe — ou se abstém (Abstenção), usando raciocínio LLM quando disponível. As evidências ordenam as opções, mas não limitam a resposta. É o único ponto do pipeline onde o LLM atua (ver LLM embutido); sua saída é um Dicionário de Mapeamento, nunca SQL.
_Avoid_: seleção, escolha

**LLM embutido**:
Princípio herdado do artigo-base (SPAPI-Tester, `docs/tcc/artigo-base.md`): o LLM não substitui o pipeline nem o fluxo do analista; entra só na etapa que exige julgamento — o de-para entre bases — entre estágios determinísticos. Ver ADR 0011.
_Avoid_: agente autônomo, IA que integra as bases, LLM gerando o join

**Dicionário de Mapeamento**:
Saída tipada da Decision Layer: Integration Key (ou Abstenção), transformação de cada lado expressa no Catálogo de Transformações, Categoria de Atrito resolvida, confiança e justificativa (raciocínio registrado). Consumida por um estágio determinístico (templates Jinja → model dbt de join + testes).
_Avoid_: resposta do LLM, JSON de saída, mapping

**Catálogo de Transformações**:
Conjunto fechado e versionado de operações tipadas (ex.: extrair trecho, concatenar colunas, remover máscara, mapear valores) com que a Decision Layer expressa como alinhar as colunas de uma Integration Key. Cada operação tem uma tradução fixa para SQL no estágio determinístico; uma chave que não cabe no catálogo leva à Abstenção. Congelado junto com o Conjunto de Teste.
_Avoid_: transformações livres, regras de transformação, DSL

**Estágio determinístico**:
Qualquer etapa do pipeline que não usa LLM e produz o mesmo resultado para a mesma entrada: coleta de evidências, geração de models dbt, execução e testes. Todo artefato executado (SQL, DAG, teste) sai de um estágio determinístico.
_Avoid_: etapa clássica, parte sem IA

**content_score**:
Score (0.0–1.0) produzido pela Content Evidence Layer para um par de colunas. Distinto do score composto existente (que pondera nome, match rate, estrutura e padrão) — o `content_score` não usa semelhança de nome como sinal. Um par com `content_score >= 0.50` é promovido ao Decision Layer mesmo que o score semântico seja próximo de zero. Limiar de promoção inicial: 0.50 (heurística a ser revisada empiricamente).
_Avoid_: score de conteúdo, pontuação de dados, nota de compatibilidade

### Chaves

**Candidate Key**:
Par de colunas (uma de cada tabela) com score semântico acima do limiar mínimo (0.30), avaliado como possível chave de integração. Pode ser simples (uma coluna) ou composta (múltiplas colunas).
_Avoid_: candidato, coluna candidata

**Integration Key**:
A chave escolhida pela Decision Layer como melhor opção para fazer o join entre duas tabelas: um Candidate Key ou uma chave proposta fora da lista (composta ou derivada). É o resultado final do pipeline, exceto quando a Decision Layer se abstém.
_Avoid_: chave de join, chave primária, coluna de ligação

**Derived Key**:
Integration Key que não existe diretamente em nenhuma tabela, mas pode ser reconstruída por transformação — ex: concatenação de campos, extração de substring, reformatação de identificador SIAFI.
_Avoid_: chave calculada, chave transformada

### Atritos de integração

**Categoria de Atrito**:
Tipo de diferença entre duas bases que impede um join direto pela Integration Key e que a Decision Layer precisa resolver. Taxonomia adaptada do artigo-base para a descoberta de chaves: a categoria de unidades do artigo (W × kW) não tem correspondente aqui, porque valores medidos não viram chave. Cada Par de Avaliação é rotulado com uma ou mais categorias.

| Categoria | Exemplo no domínio |
| --- | --- |
| Grafia/nomenclatura | `nr_empenho` × `num_empenho` × `nota_empenho` |
| Abreviação/prefixo | `cd_ug` × `codigo_unidade_gestora` |
| Formato de identificador | NE curta `2023NE000123` × SIAFI Identifier completo; CNPJ com e sem máscara; data `dd/mm/aaaa` × ISO |
| Equivalência lógica/código | situação `ATIVO` × `1`; `S`/`N` × booleano |
| Equivalência semântica | UG × unidade executora; exercício × ano |
| Derived Key | código do município → UF; UG + gestão + NE → SIAFI Identifier |
| Estrutura aninhada | chave dentro de JSON (`microrregiao.mesorregiao.UF.id`) |

_Avoid_: erro, inconsistência, problema de dados

### Avaliação

**Par de Avaliação**:
Par de tabelas (A, B) com Gabarito, rotulado com uma ou mais Categorias de Atrito. É a unidade de avaliação da Decision Layer; o **ground truth** é o conjunto dos Pares de Avaliação, cada um Par Real ou Par Perturbado.
_Avoid_: caso de teste, exemplo, par do benchmark

**Par Real**:
Par de Avaliação formado por duas tabelas públicas que existem de fato, com Gabarito anotado à mão e justificativa escrita. Pode ter várias Categorias de Atrito.
_Avoid_: par natural, caso real

**Par Perturbado**:
Par de Avaliação em que a tabela B é gerada a partir de uma tabela real aplicando exatamente uma Categoria de Atrito à chave; o Gabarito é conhecido por construção. Cada um tem uma variante com nomes de coluna anonimizados.
_Avoid_: par sintético, par artificial

**Conjunto de Teste**:
Parte do ground truth (cerca de 80% de cada tipo de par e de cada categoria) congelada antes de ajustar o agente e usada só nos experimentos finais. O restante é o **Conjunto de Desenvolvimento**, livre para ajustar a Decision Layer e o Domain Context; todo Par Real já visto durante o desenvolvimento (ex.: o par IBGE da PoC) fica nele.
_Avoid_: holdout, validação

**Gabarito**:
Conjunto de Chaves Aceitáveis de um Par de Avaliação: anotado à mão num Par Real, conhecido por construção num Par Perturbado. Vazio num Par Negativo.
_Avoid_: resposta certa, label

**Chave Aceitável**:
Integration Key considerada correta para um Par de Avaliação: colunas de A, colunas de B e a transformação que as alinha, expressa no Catálogo de Transformações. Um par pode ter várias (ex.: no par IBGE, o prefixo do código do município ou o `UF.id` aninhado).
_Avoid_: chave certa, chave esperada

**Par Negativo**:
Par de Avaliação cujo Gabarito é vazio: não existe Integration Key entre as tabelas, e a resposta correta é a Abstenção.
_Avoid_: par sem chave, caso negativo

**Abstenção**:
Saída da Decision Layer que declara não haver Integration Key entre as duas tabelas. É uma resposta, não uma falha.
_Avoid_: erro, sem resultado, falha

**Join de Referência**:
Junção obtida ao aplicar uma Chave Aceitável do Gabarito, com sua transformação. Base de comparação do Acerto de Execução.
_Avoid_: join esperado, join correto

**Cobertura de Candidatos**:
Fração dos Pares de Avaliação em que alguma Chave Aceitável está entre os Candidate Keys entregues à Decision Layer. É o teto do pipeline sem LLM e separa erro do estágio de evidências de erro de decisão.
_Avoid_: recall, cobertura (sem qualificador)

**Acerto de Chave**:
A Integration Key escolhida coincide, em colunas, com alguma Chave Aceitável do Gabarito; num Par Negativo, a Decision Layer se absteve.
_Avoid_: acurácia, acerto (sem qualificador)

**Acerto de Execução**:
O join produzido com a Integration Key e a transformação propostas reproduz o Join de Referência acima de um limiar fixado junto com o Conjunto de Teste. Separa colunas certas com transformação errada de uma decisão que de fato integra as bases.
_Avoid_: acerto de join, validação

### Processo de construção (QP5)

**Spec**:
Documento em `docs/specs/` com problema, escopo, contrato e critérios de aceite verificáveis, aprovado antes da implementação de um incremento.
_Avoid_: PRD, plano, especificação informal

**Teste-Oráculo**:
Teste escrito pela autora a partir dos critérios de aceite de uma Spec, antes da implementação e fora do alcance do agente. É o juiz independente dos dois braços de uma Comparação Pareada; os testes que o agente escreve não contam como oráculo.
_Avoid_: teste de aceite, teste do agente

**Comparação Pareada**:
O mesmo incremento implementado duas vezes pelo mesmo agente, a partir do mesmo commit: o **braço com spec** recebe a Spec completa; o **braço sem spec**, só o problema. Só o braço com spec entra no repositório.
_Avoid_: A/B, experimento controlado

### Domínio orçamentário federal (Brasil)

**Nota de Empenho (NE)**:
Documento SIAFI de comprometimento orçamentário. Identificador no formato `ANONEséquência` (curto, ex: `2023NE000123`) ou no formato SIAFI completo `[UG 6dig][gestão 5dig][ANO][NE][seq 6dig]`.
_Avoid_: empenho, nota fiscal

**Convênio**:
Acordo formal entre entes governamentais para transferência de recursos. Identificador no formato `NNNNNN/AAAA`.
_Avoid_: contrato, instrumento, parceria

**UG (Unidade Gestora)**:
Unidade administrativa responsável pela execução orçamentária. Código de 6 dígitos no SIAFI.
_Avoid_: órgão, unidade

**Exercício**:
Ano fiscal de referência de um documento orçamentário. Sempre um inteiro de 4 dígitos.
_Avoid_: ano, competência, período

**SIAFI Identifier**:
Identificador estruturado do SIAFI no formato `[UG 6dig][gestão 5dig][ANO 4dig][tipo 2 letras][seq 6dig]`. Tipos conhecidos: NE (empenho), NC (nota de crédito), PF (pagamento), OB (ordem bancária).
_Avoid_: identificador completo, código SIAFI

## Example dialogue

> **Dev:** Encontrei dois campos com match rate baixo — 12% global. Isso elimina como Integration Key?
>
> **Domain expert:** Não necessariamente. Verifica se o match sobe quando filtra por Exercício. Bases do SIAFI e do Transfere têm cobertura temporal diferente — a Derived Key pode ter 96% de match dentro do mesmo ano.
>
> **Dev:** O campo de A parece ser uma Nota de Empenho no formato curto. Como junto com o de B que está no formato SIAFI Identifier?
>
> **Domain expert:** Reconstrói: pega o ANO e a sequência do campo curto, concatena com o cd_ug e cd_gestao de A — isso te dá o SIAFI Identifier. Aí o match vai para perto de 100%.
