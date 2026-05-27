# Integração Semântica de Bases de Dados

Sistema genérico para identificação de chaves de integração entre tabelas CSV, com suporte a enriquecimento por contexto de domínio. Desenvolvido no contexto do TCC de integração de bases orçamentárias federais brasileiras.

## Language

### Pipeline

**Integration Pipeline**:
A sequência ordenada de cinco etapas que transforma dois arquivos CSV em uma chave de integração documentada: validar-contexto → analisar-tabela → comparar-colunas → identificar-chave → gerar-relatorio.
_Avoid_: fluxo, workflow, processo

**Domain Context**:
Arquivo JSON reutilizável que descreve o vocabulário semântico de um domínio específico — grupos de colunas equivalentes, padrões regex de identificadores e pesos de confiança. Gerado uma vez por domínio pela skill `definir-contexto` e consumido por todas as demais skills.
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
Papel da skill `identificar-chave` no pipeline: recebe as evidências da Evidence Layer ou da Content Evidence Layer e decide a melhor chave de integração, usando raciocínio LLM quando disponível.
_Avoid_: seleção, escolha

**content_score**:
Score (0.0–1.0) produzido pela Content Evidence Layer para um par de colunas. Distinto do score composto existente (que pondera nome, match rate, estrutura e padrão) — o `content_score` não usa semelhança de nome como sinal. Um par com `content_score >= 0.50` é promovido ao Decision Layer mesmo que o score semântico seja próximo de zero. Limiar de promoção inicial: 0.50 (heurística a ser revisada empiricamente).
_Avoid_: score de conteúdo, pontuação de dados, nota de compatibilidade

### Chaves

**Candidate Key**:
Par de colunas (uma de cada tabela) com score semântico acima do limiar mínimo (0.30), avaliado como possível chave de integração. Pode ser simples (uma coluna) ou composta (múltiplas colunas).
_Avoid_: candidato, coluna candidata

**Integration Key**:
O Candidate Key escolhido pela Decision Layer como melhor opção para fazer o join entre duas tabelas. É o resultado final do pipeline.
_Avoid_: chave de join, chave primária, coluna de ligação

**Derived Key**:
Integration Key que não existe diretamente em nenhuma tabela, mas pode ser reconstruída por transformação — ex: concatenação de campos, extração de substring, reformatação de identificador SIAFI.
_Avoid_: chave calculada, chave transformada

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
