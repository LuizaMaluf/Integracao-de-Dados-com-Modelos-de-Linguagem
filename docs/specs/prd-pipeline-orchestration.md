# PRD: Pipeline de Orquestração de Integração de Bases

**Data:** 2026-05-26  
**Status:** Ready for implementation

---

## Problem Statement

O usuário precisa executar cada skill manualmente, em sequência, para integrar duas tabelas CSV: primeiro perfila as tabelas, depois compara colunas específicas, depois identifica a chave, depois gera o relatório. Não existe um fluxo orquestrado — o usuário precisa saber qual skill chamar em qual ordem, passar os paths corretos entre etapas, e repetir isso para cada novo par de tabelas. Além disso, o conhecimento de domínio (grupos semânticos, padrões regex) está duplicado dentro de cada skill e só cobre o domínio orçamentário federal, impedindo o uso em outros contextos.

---

## Solution

Introduzir uma skill orquestradora (`integrar-bases`) que executa o Integration Pipeline completo a partir de dois arquivos CSV, encadeando as skills existentes via arquivo com paths previsíveis. Paralelamente, extrair o conhecimento de domínio para um Domain Context reutilizável por domínio, gerado pela nova skill `definir-contexto`. O pipeline valida a cobertura do contexto no início de cada execução e enriquece os resultados quando o contexto está disponível, mas funciona de forma genérica sem ele.

---

## User Stories

1. Como analista de dados, quero fornecer dois arquivos CSV e receber um relatório completo de integração com um único comando, para não precisar gerenciar manualmente a sequência de análises.

2. Como analista, quero que o pipeline identifique automaticamente quais colunas comparar, para não precisar especificar pares de colunas manualmente antes de saber quais são candidatas.

3. Como analista, quero que o pipeline me avise quando o Domain Context existente cobre menos de 60% das colunas das minhas tabelas, para saber quando devo atualizar o contexto antes de continuar.

4. Como analista, quero gerar um Domain Context descrevendo um domínio em linguagem natural e ter os grupos semânticos e padrões criados automaticamente, para poder usar o sistema em bases fora do domínio orçamentário.

5. Como analista, quero reutilizar um Domain Context já gerado em múltiplas integrações do mesmo domínio, para não precisar redefinir o vocabulário a cada novo par de tabelas.

6. Como analista, quero que o pipeline funcione mesmo sem um Domain Context configurado, para poder usar em domínios desconhecidos sem bloqueio.

7. Como analista, quero que cada etapa do pipeline salve seu resultado em um arquivo com nome previsível, para poder inspecionar ou retomar de qualquer ponto sem reprocessar tudo.

8. Como analista, quero que a etapa de comparação de colunas seja executada automaticamente nos pares mais prováveis identificados pelo perfil das tabelas, para obter evidências de compatibilidade sem intervenção manual.

9. Como analista, quero que a skill `comparar-colunas` ainda funcione de forma manual quando eu quiser testar uma hipótese específica fora do pipeline, para não perder a capacidade de exploração pontual.

10. Como analista, quero que o relatório final referencie o Domain Context usado (ou indique que nenhum foi aplicado), para que o resultado seja rastreável e reproduzível.

11. Como analista, quero que o pipeline emita um aviso claro quando a confiança da Integration Key estiver abaixo de 0.6, para saber quando revisar manualmente antes de usar o join em produção.

12. Como analista de um domínio diferente do orçamentário (ex: saúde, educação), quero gerar um Domain Context específico para meu domínio e usar o mesmo pipeline, para não precisar de uma ferramenta separada.

13. Como analista, quero que a validação do Domain Context me mostre quais colunas das tabelas de entrada não foram reconhecidas, para decidir se devo atualizar o contexto ou aceitar a cobertura parcial.

14. Como analista, quero que a skill `integrar-bases` me informe claramente em qual etapa o pipeline está a cada momento, para acompanhar o progresso sem ambiguidade.

15. Como analista, quero que todas as skills do pipeline tenham inputs e outputs explicitamente declarados, para poder entender o fluxo de dados sem ler a implementação completa de cada skill.

16. Como desenvolvedor do TCC, quero que o pipeline genérico demonstre bons resultados em pelo menos dois domínios distintos, para validar a abordagem como contribuição acadêmica.

---

## Implementation Decisions

### Módulos a construir

**`definir-contexto` (skill nova):**  
Recebe uma descrição do domínio em linguagem natural e produz um `context_{domínio}.json` com grupos semânticos de colunas, padrões regex de identificadores e o nome canônico do domínio. Usa LLM para inferir os grupos a partir da descrição. Salva em `output/contexts/`.

**`integrar-bases` (skill nova — orquestradora):**  
Recebe dois paths de CSV e um Domain Context opcional. Executa as 5 etapas em sequência: validar-contexto → analisar-tabela (×2) → comparar-colunas → identificar-chave → gerar-relatorio. Não possui lógica de decisão própria — apenas encadeia, passa paths e reporta progresso. Primeira versão sem ramificação condicional.

**Context Loader (módulo Python novo):**  
Carrega e valida um `context_{domínio}.json`. Interface simples: recebe path, retorna grupos semânticos e padrões, ou retorna os defaults do domínio orçamentário se nenhum contexto for fornecido. É o único ponto do sistema que conhece o schema do arquivo de contexto.

**Context Validator (módulo Python novo):**  
Recebe as colunas das duas tabelas de entrada e um Domain Context carregado. Calcula Context Coverage: quantas colunas são reconhecidas pelos grupos semânticos do contexto. Retorna percentual, lista de colunas reconhecidas e lista de colunas não reconhecidas. Limiar de aviso: 60%.

### Mudanças nas skills existentes

**`analisar-tabela`:**  
Adicionar `input:` / `output:` ao frontmatter. Remover redeclaração interna de DOMAIN_GROUPS e PATTERNS — passar a ler do Domain Context se disponível, usar defaults hardcoded como fallback.

**`comparar-colunas`:**  
Adicionar `input:` / `output:` ao frontmatter. Adicionar modo automático: quando recebe dois arquivos de perfil (output do `analisar-tabela`) sem colunas especificadas, seleciona automaticamente os pares candidatos usando primary key candidates + domain group matching. Manter modo manual existente para uso exploratório.

**`identificar-chave`:**  
Adicionar `input:` / `output:` ao frontmatter. Adaptar para consumir o output consolidado do `comparar-colunas` como Evidence Layer — a etapa de geração de candidatos já foi feita; `identificar-chave` recebe as evidências e decide.

**`gerar-relatorio`:**  
Adicionar `input:` / `output:` ao frontmatter. Incluir no relatório qual Domain Context foi usado (nome do domínio e cobertura) ou nota de ausência.

### Contrato de I/O no frontmatter

Cada `SKILL.md` declara:

```yaml
input:
  - type: csv | json
    path: <path com placeholders {table_a}, {table_b}>
    optional: true | false
output:
  - type: json | markdown
    path: output/<prefixo>_{table_a}__{table_b}.json
```

### Schema do Domain Context

```json
{
  "domain_name": "string",
  "version": "YYYY-MM-DD",
  "semantic_groups": {
    "<group_name>": ["alias1", "alias2", "..."]
  },
  "key_patterns": {
    "<pattern_name>": "<regex>"
  }
}
```

### Mecanismo de encadeamento

File-based: cada skill lê do output da etapa anterior usando paths previsíveis derivados dos nomes das tabelas de entrada. O orquestrador resolve os paths antes de chamar cada skill.

### Seleção automática de pares em `comparar-colunas`

No modo automático, seleciona pares assim:
1. Cruza primary key candidates de A com primary key candidates de B
2. Para cada par, calcula semantic score (nome + grupo de domínio do contexto)
3. Mantém pares com score ≥ 0.30
4. Limita a top-15 pares por score semântico (antes de calcular match rate)

### Injeção de contexto nos módulos Python

O Context Loader alimenta `CandidateGenerator` com os grupos semânticos do Domain Context em vez dos defaults de `src/config/domain.py`. Os defaults permanecem como fallback quando nenhum contexto é fornecido.

---

## Testing Decisions

**O que faz um bom teste aqui:**  
Testar comportamento externo observável, não detalhes de implementação. Para módulos de análise: dado um input (série de valores ou par de colunas), o output (score, match rate, cobertura) deve ser determinístico e correto. Para o Context Validator: dado um conjunto de colunas e um contexto, a cobertura calculada deve ser exata.

**Módulos a testar:**

- **Context Loader** — deve retornar defaults quando context file está ausente; deve falhar com erro claro quando o arquivo existe mas o schema é inválido.
- **Context Validator** — dado um contexto e uma lista de colunas, deve calcular Context Coverage corretamente; deve identificar colunas não reconhecidas.
- **Seleção automática de pares (comparar-colunas)** — dado o output de dois `analisar-tabela`, deve selecionar os pares corretos acima do limiar semântico.
- **CandidateGenerator com contexto injetado** — deve boostar scores de pares que pertencem ao mesmo grupo do Domain Context fornecido.

**Módulos já testáveis que merecem cobertura adicional:**
- `semantic_score` — casos de edge: nomes idênticos, nomes sem nenhuma semelhança, mesmo grupo semântico com nomes diferentes.
- `overlap_stats` — cobertura assimétrica (B é subconjunto de A).

---

## Out of Scope

- Suporte a mais de duas tabelas de entrada por execução de pipeline
- Lógica condicional no orquestrador (ex: pular etapas com base em confiança)
- Interface gráfica ou web
- Integração com banco de dados (o pipeline opera exclusivamente sobre CSV)
- Detecção automática de domínio sem input do usuário (a skill `definir-contexto` requer descrição explícita)
- Versionamento ou histórico de Domain Contexts
- Execução paralela das etapas do pipeline

---

## Further Notes

O Domain Context resolve simultaneamente dois problemas: elimina a duplicação de conhecimento de domínio entre skills e torna o pipeline portável para domínios além do orçamentário federal. A decisão de torná-lo opcional (com fallback para os grupos hardcoded existentes) preserva a compatibilidade com o uso atual sem quebrar nada.

A separação entre Evidence Layer (`comparar-colunas`) e Decision Layer (`identificar-chave`) reflete uma distinção real no processo de análise — coleta de dados e tomada de decisão são responsabilidades distintas. Essa separação também facilita inspecionar os dados brutos antes da decisão do LLM, o que é relevante para a avaliação acadêmica do TCC.

O limiar de Context Coverage de 60% é uma heurística inicial. Deve ser revisado empiricamente após testes com os domínios reais usados no TCC.
