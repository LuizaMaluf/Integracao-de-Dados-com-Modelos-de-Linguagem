# PRD: Content Evidence Layer — skill `comparar-dados`

**Data:** 2026-05-27  
**Status:** Ready for implementation

---

## Problem Statement

O `mapear-integracoes` rejeita pares de tabelas com afinidade semântica < 0.45 — casos em que nenhum par de colunas passou o limiar de semelhança de nome. No entanto, tabelas podem conter dados semanticamente equivalentes em colunas com nomes completamente não relacionados: uma coluna chamada `ds_documento` pode conter os mesmos valores que uma coluna chamada `nr_nota`, e uma coluna com identificadores curtos (ex: `2023NE000123`) pode ser derivável de uma coluna com SIAFI Identifiers completos em outra tabela.

O pipeline atual não tem nenhum mecanismo para recuperar esses pares rejeitados por nome. A Integration Key existe nos dados — mas o sistema nunca a encontra porque o único sinal de busca é o nome da coluna.

---

## Solution

Introduzir a skill `comparar-dados` como uma Content Evidence Layer: ela recebe pares de tabelas rejeitados pelo `mapear-integracoes` e produz Candidate Keys usando sinais extraídos dos valores reais das colunas, sem depender de semelhança de nome.

A skill computa três sinais para cada par de colunas: compatibilidade de formato (regex dominante), sobreposição direta de valores e sobreposição de substring (sinal de Derived Key). Esses sinais são combinados em um `content_score` que, acima de 0.50, promove o par diretamente ao Decision Layer (`identificar-chave`) para raciocínio LLM.

O `analisar-tabela` é estendido para reportar distribuição de exercícios no perfil, permitindo que o orquestrador alinhe temporalmente os samples antes da comparação.

---

## User Stories

1. Como analista, quero que pares de tabelas rejeitados pelo `mapear-integracoes` por baixa afinidade semântica sejam automaticamente reanalisados por conteúdo, para que Integration Keys baseadas em dados — não em nomes de coluna — não sejam perdidas.

2. Como analista, quero que a skill identifique quando duas colunas com nomes não relacionados têm o mesmo formato de valor (ex: ambas contêm padrões `^\d{4}NE\d{6}$`), para ter evidência de que representam o mesmo conceito.

3. Como analista, quero que a skill detecte quando valores de col_a aparecem como substrings de valores de col_b, para que Derived Keys sejam sinalizadas ao `identificar-chave` mesmo sem match direto de valores.

4. Como analista, quero que a proposta de transformação necessária para a Derived Key venha do `identificar-chave` (LLM), não da `comparar-dados`, para manter a separação entre Evidence Layer e Decision Layer.

5. Como analista, quero que pares com `content_score >= 0.50` sejam promovidos automaticamente ao `identificar-chave`, para que o LLM decida com base em evidência de conteúdo.

6. Como analista, quero que o `content_score` seja um campo distinto no Candidate Key — não combinado com o score semântico existente — para que o caminho de descoberta fique claro no relatório final.

7. Como analista, quero que o sample de cada coluna use as primeiras 100 linhas não-nulas daquela coluna, para evitar que nulos contaminem artificialmente os sinais de conteúdo.

8. Como analista, quero que o perfil gerado pelo `analisar-tabela` inclua a distribuição de exercícios da tabela (quais anos existem e quantas linhas cada um tem), para que o orquestrador consiga alinhar temporalmente os samples quando as tabelas cobrem períodos diferentes.

9. Como analista, quero que o orquestrador detecte a interseção de exercícios entre as duas tabelas e restrinja o sample a esse período comum, para evitar que `content_score = 0` reflita diferença de período em vez de ausência de relação.

10. Como analista, quero que a skill use apenas compatibilidade de dtype como pré-filtro antes de computar os sinais de conteúdo, sem filtrar por unicidade, para que joins fato-dimensão — onde a coluna do lado fato tem unicidade baixa — não sejam descartados antes de ser avaliados.

11. Como analista, quero que a skill `comparar-dados` possa ser invocada manualmente para testar uma hipótese específica fora do fluxo do `mapear-integracoes`, para manter a capacidade de exploração pontual.

12. Como analista, quero que o relatório final identifique quando a Integration Key foi descoberta via Content Evidence Layer (e não via semântica de nome), para que o resultado seja rastreável e a contribuição do caminho de conteúdo seja auditável.

13. Como desenvolvedor do TCC, quero que a skill seja uma contribuição isolável e mensurável — com precision e recall calculáveis separadamente do caminho semântico — para poder demonstrar o valor do Content Evidence Layer como contribuição acadêmica.

14. Como analista de domínios não-orçamentários, quero que a `comparar-dados` funcione sem Domain Context configurado, para que a skill seja tão genérica quanto o resto do pipeline.

---

## Implementation Decisions

### Camada 1 — Modificações fundacionais (pré-requisito para tudo abaixo)

**`CandidateKey` (dataclass):**  
Adicionar campo `content_score: float | None = None`. Valor `None` indica candidato oriundo do caminho semântico normal; valor numérico indica descoberta via Content Evidence Layer. Essa distinção é necessária para que o `identificar-chave` e o relatório final saibam qual caminho produziu o candidato.

**`analisar-tabela` (skill existente):**  
Adicionar ao JSON de saída uma chave `exercicio_distribution`: dicionário `{ano: contagem}` para a coluna de exercício detectada, ou `null` se nenhuma for identificada. O `mapear-integracoes` e o `comparar-dados` dependem dessa informação para alinhar temporalmente os samples.

### Camada 2 — Novos módulos Python

**`ContentAnalyzer`:**  
Encapsula os três sinais de conteúdo e a fórmula hierárquica do `content_score`. Interface simples: recebe duas séries Pandas (os samples), retorna `ContentEvidence` com os três sinais e o score final. É o único módulo que conhece a fórmula de combinação. Testável em isolamento completo.

**`ExercicioProfiler`:**  
Detecta se uma tabela tem coluna de exercício (via Domain Context ou regex `^\d{4}$` com alta cobertura) e retorna a distribuição de anos presentes. Alimenta o campo `exercicio_distribution` adicionado ao `analisar-tabela`.

### Camada 3 — Nova skill e integração

**`comparar-dados` (skill nova — Content Evidence Layer):**  
Recebe dois arquivos CSV (ou dois perfis de `analisar-tabela`) e a interseção de exercícios detectada pelo orquestrador. Para cada par de colunas que passa o pré-filtro de dtype, computa os três sinais de conteúdo e produz Candidate Keys com `content_score`. Promove ao `identificar-chave` os pares com `content_score >= 0.50`.

**`mapear-integracoes` (skill existente — extensão):**  
Após gerar o mapa semântico, iterar sobre pares com afinidade < 0.45 e invocar `comparar-dados` para cada um. Incorporar ao mapa final os pares promovidos via conteúdo, marcados com `discovery_method: "content"`.

### Fórmula do content_score

Hierárquica em dois níveis:

- Se `format_match = True` (ambas as colunas têm o mesmo regex dominante):  
  `content_score = max(overlap_rate, substring_match_rate)`

- Se `format_match = False`:  
  `content_score = 0.6 × overlap_rate + 0.4 × substring_match_rate`

O `format_match` confirma compatibilidade estrutural e eleva o peso dos sinais de valor. Sem ele, os sinais de valor têm peso reduzido.

### Sinais computados pelo ContentAnalyzer

- **format_match**: booleano — ambas as colunas compartilham o mesmo `best_domain_match` retornado por `detect_pattern`. Reutiliza o `pattern_detector` existente.
- **overlap_rate**: fração dos 100 valores de col_a encontrados diretamente no conjunto de valores de col_b. Reutiliza `overlap_stats` existente.
- **substring_match_rate**: fração dos 100 valores de col_a encontrados como substring em algum valor de col_b (ou vice-versa, usando o máximo dos dois sentidos). Sinaliza relação de Derived Key.

### Sampling

Para cada par `(col_a, col_b)` avaliado: extrair as primeiras 100 linhas não-nulas de col_a e as primeiras 100 linhas não-nulas de col_b, dentro do exercício de interseção quando disponível. O sample é determinístico (posição, não aleatório).

### Pré-filtro de pares

Antes de computar qualquer sinal de conteúdo: descartar o par se os dtypes das duas colunas forem incompatíveis (reusa `dtype_compatible` de `structural.py`). Sem filtro de unicidade — preserva joins fato-dimensão onde a coluna do lado fato tem unicidade próxima de zero.

### Limiar de promoção

`content_score >= 0.50` promove o par ao Decision Layer. Heurística inicial — a ser revisada empiricamente após testes com os domínios do TCC.

---

## Testing Decisions

**O que faz um bom teste aqui:**  
Testar comportamento externo do `ContentAnalyzer` dado inputs controlados. A fórmula deve ser determinística: mesmos dois arrays de valores produzem sempre o mesmo `content_score`. Não testar detalhes internos de qual regex foi detectado — testar se o score produzido está correto dado os sinais de entrada.

**Módulos a testar:**

- **`ContentAnalyzer` — ramo com format_match**: dado dois arrays com o mesmo regex dominante e alta sobreposição direta, `content_score` deve ser `max(overlap_rate, substring_match_rate)` e próximo de 1.0.
- **`ContentAnalyzer` — ramo sem format_match**: dado arrays sem formato comum mas com alta sobreposição, `content_score` deve ser `0.6 × overlap_rate + 0.4 × substring_match_rate`.
- **`ContentAnalyzer` — detecção de Derived Key via substring**: dado `["2023NE000123"]` e `["123456789002023NE000123"]`, o `substring_match_rate` interno deve ser 1.0 e o `content_score` resultante deve refletir isso. Dado arrays sem relação de substring, `content_score` deve ser próximo de zero.
- **`ExercicioProfiler`**: dado uma série com valores `["2022", "2022", "2023", "2023", "2023"]`, retornar `{"2022": 2, "2023": 3}`. Dado uma série sem padrão de ano (ex: nomes de municípios), retornar `null`.
- **`CandidateKey.content_score`**: verificar que o campo `None` distingue candidatos do caminho semântico de candidatos do caminho de conteúdo.
- **Promoção ao Decision Layer**: dado um `content_score = 0.51`, o par é incluído no output para `identificar-chave`; dado `content_score = 0.49`, não é incluído.

---

## Out of Scope

- Proposta automática de transformação para Derived Keys — responsabilidade do `identificar-chave` (LLM)
- Alinhamento temporal por granularidade menor que exercício fiscal (mês, trimestre, bimestre)
- Suporte a mais de dois sinais de conteúdo adicionais além dos três definidos
- Execução paralela dos pares de colunas dentro da skill
- Cache de resultados de `comparar-dados` entre execuções do `mapear-integracoes`
- Ajuste automático do limiar de promoção com base em feedback do usuário

---

## Further Notes

O `comparar-dados` resolve um blind spot estrutural do pipeline: a suposição de que colunas relacionadas têm nomes parecidos. Bases do SIAFI, Transfere e MIR nomeiam o mesmo conceito de formas radicalmente diferentes — `nr_nota`, `ds_documento`, `id_siafi`, `cd_referencia` podem ser a mesma Nota de Empenho. Nenhuma semelhança de nome vai capturar isso.

A separação entre Content Evidence Layer (`comparar-dados`) e Decision Layer (`identificar-chave`) é deliberada e segue o mesmo padrão Evidence/Decision já estabelecido no pipeline. A skill de conteúdo não propõe transformações — ela só diz "esses valores parecem relacionados". O LLM, com acesso aos padrões detectados e ao Domain Context, decide como reconstruir a chave e propõe a transformação necessária.

O `content_score` como campo distinto no `CandidateKey` serve também ao propósito acadêmico: é possível medir quantos pares foram descobertos exclusivamente pelo caminho de conteúdo, com que precisão, e comparar com o caminho semântico. Essa separabilidade é necessária para a avaliação da contribuição no TCC.
