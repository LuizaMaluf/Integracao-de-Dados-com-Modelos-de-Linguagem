# Cobertura do Catálogo de Transformações

Quantas das condições de join do [inventário](inventario-govhub.md) o Catálogo de Transformações expressa, com as definições da [ADR 0013](../adr/0013-catalogo-de-transformacoes-fechado.md). Recontagem de 2026-11-15. A contagem mede ajuste, não generalização: o catálogo saiu do mesmo inventário (ver "Ajuste × generalização" em [`proposta.md`](proposta.md)).

## Regras da contagem

- **Universo**: as 29 condições do inventário, menos as 3 com chave em CPF (#19, #27 e #28), dão 26.
- **Operações por lado**: soma das operações de todas as colunas da chave naquele lado; o limite é 3 (ADR 0013, decisão 2). Cada `trecho` usado dentro de `concatenar` conta.
- **Filtros** do join em produção são escopo do par e não contam como operação.
- **Cascatas**: cada etapa é uma Chave Aceitável; a classe da condição segue a primeira etapa (ADR 0013, decisão 6).
- **Classes**:
  - **A**: cabe sem `extrair_identificador`;
  - **B**: precisa de `extrair_identificador(tipo)` na primeira etapa;
  - **C**: fora do catálogo; a resposta do pipeline é Abstenção por transformação fora do catálogo.
- **Fontes**: as transformações vêm do inventário, conferido no código em 2026-11-05. O #8 e o #10 foram relidos no `data-application-mir` (HEAD `9807b9a`, 2026-11-13) e o #18 no `data-application-gov-hub` local.

## Resumo

| Contagem | A | A + B | C | Excluídas |
| --- | --- | --- | --- | --- |
| Pôster do CAIN 2027 (rascunho do catálogo; B = `extrair_identificador` em alguma etapa; 8 condições sem definição) | 14/26 (54%) | 18/26 (69%) | — | 3 |
| ADR 0013, com a mesma regra do pôster para B | 19/26 (73%) | 23/26 (88%) | 3/26 (12%) | 3 |
| **ADR 0013, classe pela primeira etapa** | **21/26 (81%)** | **23/26 (88%)** | **3/26 (12%)** | 3 |

As 8 condições sem definição no pôster eram #4, #10, #11, #14, #17, #18, #25 e #26. Com a ADR 0013, cinco entram na classe A (#4, #10, #11, #14 e #25) e três ficam fora (#17, #18 e #26). A regra da primeira etapa leva #2 e #3 de B para A: a primeira etapa de cada um cabe sem extração, e a extração aparece só num fallback.

## Por condição

"Lado 1" é a primeira tabela da condição no inventário; "lado 2", a segunda. Os números entre parênteses são operações por lado.

| # | Lado 1 | Lado 2 | Classe | Observação |
| --- | --- | --- | --- | --- |
| 1 | `ne` —; `cnpj_cpf`: `remover_mascara` (1) | `ne_ccor`: `trecho(fim, 12)`, `normalizar_texto(caixa)` (2) | A | CPF quando o favorecido é pessoa física: escopo restrito a pessoa jurídica |
| 2 | etapa 1, `num_processo`: `remover_mascara` (1) | `remover_mascara` (1) | A | Fallbacks do #1. A etapa por `info_complementar` usa `concatenar` (1) × `substring(... '^([0-9]+) -')`, que cabe como `trecho` com delimitador literal `' -'` se o formato se mantiver, ou senão como `extrair_identificador` |
| 3 | etapa 1, `(ne, cnpj_cpf)`: como no #1 | como no #1 | A | Cascata `ne` → `num_processo` → `info_complementar`, como no #1 e no #2 |
| 4 | `contrato_id` —; data: `trecho(delimitador)`, `converter_data(mês)` (2) | `contrato_id` —; `concatenar(ano, mês)`, `converter_data(mês)` (2) | A | `split_part` vira `trecho` com delimitador literal |
| 5 | `ne_ccor` — | `concatenar(UG, gestão, número)`, `normalizar_texto(caixa)` (2) | A | Exemplo de Derived Key do `CONTEXT.md` |
| 6 | `nc`: `trecho(início, 6)`, `trecho(fim, 12)` (2) | — | A | Decompõe o SIAFI Identifier em UG e documento |
| 7 | `trecho(fim, 12)`, `normalizar_texto(caixa, espaços)` (2) | `normalizar_texto(caixa, espaços)` (1) | A | |
| 8 | etapa 1: `extrair_identificador(TED)` em `ne_ccor_descricao` (1) | — | B | Cascata de 16 passos; ver a tabela abaixo |
| 9 | — | — | A | Única igualdade direta entre colunas sem transformação |
| 10 | `num_transf`: `converter_tipo(texto)`, `normalizar_texto(espaços)`, `preencher_zeros(largura)` (3) | idem (3) | A | No limite. `ltrim(..., '0')` só em `num_transf`; `plano_acao` sem transformação |
| 11 | fonte —; `ptres`: `trecho(delimitador '.', 1)` (1) | — | A | |
| 12 | `extrair_identificador(convênio)`, `converter_tipo(inteiro)` (2) | — | B | Número do convênio no texto da NE |
| 13 | `converter_tipo(texto)` (1) | — | A | `left(ne_ccor,6)='810008'` é escopo do par |
| 14 | `normalizar_texto(caixa, espaços, acentos)` (1) | `trecho(delimitador '/', 1)`, `normalizar_texto(caixa, espaços)` (2) | A | Desempate por data de filiação fora do catálogo e do escopo; Join de Referência sem desempate |
| 15 | `normalizar_texto(caixa, espaços)` (1) | idem (1) | A | |
| 16 | `converter_tipo(inteiro)` (1) | — | A | |
| 17 | `mapear_valores('GABIN-IPEA' → 'GABIN')` | — | C | Par fora do Glossário; pôr o par no Glossário copiaria o Gabarito |
| 18 | `funcao`: `remover_mascara`, `trecho`, `trecho`, `concatenar` (4); sigla com o de-para do #17 | `cod_funcao`: `trecho`, `trecho`, `concatenar` (3) | C | Passa do limite no lado SIORG |
| 19 | — | — | Excluída | Chave é CPF |
| 20 | `remover_mascara` (1) | `remover_mascara` (1) | A | `length >= 5` é escopo. O SQL remove todo caractere não numérico, mais do que `.`, `/`, `-` e espaços |
| 21 | `converter_tipo(texto)` (1) | — | A | Sisbolsas: só colunas não pessoais no snapshot |
| 22 | `remover_mascara`, `preencher_zeros(8)` (2) | idem (2) | A | UDF `normalize_apf` |
| 23 | `trecho(fim, 6)` (1) | `trecho(início, 6)` (1) | A | |
| 24 | `normalizar_texto(espaços)` (1) | — | A | `nullif(..., '')` trata vazio como nulo |
| 25 | `ano` —; `converter_data(trimestre)` (1) | — | A | Trimestre derivado do mês |
| 26 | `normalizar_texto` ×2, `concatenar` (3) | `normalizar_texto`, `mapear_valores(código de UF → sigla)`, `normalizar_texto`, `concatenar` (4) | C | Passa do limite no lado 2. Ver "Pendências" |
| 27 | — | — | Excluída | Chave é CPF |
| 28 | — | — | Excluída | Chave é CPF; model desativado, lido em minc `813aa20` |
| 29 | `agencia`, `conta`: `converter_tipo(inteiro)` (2) | — | A | Passo de ingestão em Python, não model dbt |

## Cascata do #8

`num_transf` sai de `ne_ccor_descricao` e de outros campos da NE por uma cascata em `mir/models/empenhos_ted_dbt/silver/empenhos_ted_cascata.sql`, com os padrões na macro `ted_num_transf_metodos()` de `macros/mir_silver/regex_vinculo.sql` (MIR HEAD `9807b9a`). Cada NE fica com o primeiro método que resolve.

| Ordem | Método | Campo | Tipo | No catálogo |
| --- | --- | --- | --- | --- |
| 1 | método 1 | `ne_ccor_descricao` | regex | `extrair_identificador(TED)` |
| 2 | método 2 | `ne_ccor_descricao` | regex | `extrair_identificador(TED)` |
| 3 | método 3 | `ne_ccor_descricao` | regex | `extrair_identificador(TED)` |
| 4 | método 4 | `fonte_recursos_detalhada_descricao` | regex | `extrair_identificador(TED)` |
| 5 | método 5 | `ne_info_complementar` | regex do campo inteiro (`^…$`) | Sem transformação: igualdade direta com o campo |
| 6 | método 10 | `doc_observacao` | regex | `extrair_identificador(TED)` |
| 7 | método 11 | `ne_ccor_descricao` | regex | `extrair_identificador(TED)` |
| 8 | método 14 | `ne_ccor_descricao` | regex | `extrair_identificador(TED)` |
| 9 | método 15 | `fonte_recursos_detalhada_descricao` | regex | `extrair_identificador(TED)` |
| 10 | método 16 | `ne_ccor_descricao` | regex | `extrair_identificador(TED)` |
| 11 | método 6 | outras linhas da mesma `ne_ccor` | herança entre linhas | Fora: não é chave entre as duas tabelas |
| 12 | método 7 | `ne_ccor_descricao` | regex + normalização do ano por CASE | Fora: número/ano na numeração do órgão, com ano de 2 dígitos expandido e ano preenchido pelo grupo |
| 13 | método 8 | `doc_observacao` | regex + normalização do ano por CASE | Fora: como o método 7 |
| 14 | método 9 | outras linhas do mesmo órgão e número de TED normalizado | herança entre linhas | Fora: não é chave entre as duas tabelas |
| 15 | página gov.br | `ne_ccor_descricao` × `ted_gov_br` | regex | Fora: depende de uma terceira tabela |
| 16 | empenho de origem | `ne_ccor_descricao` × NE de origem | regex | Fora: liga a NE a outra NE da mesma tabela (`left(ne_ccor, 6)`, `right(ne_ccor, 12)`) |

Contagem: 16 passos, 14 por regex e 2 por herança entre linhas (métodos 6 e 9). O empenho de origem também herda o `num_transf` de outra linha, mas conta como regex, porque é o regex que acha a NE de origem. Das 16 etapas, 9 cabem com `extrair_identificador` e 1 sem transformação (método 5); as outras 6 ficam fora.

## Pendências

- **#26 como chave composta.** Sem `concatenar`, a chave (município, UF) cabe em 3 operações no lado 2, mas só se o de-para código de UF → sigla estiver no Glossário. É uma tabela pública do IBGE, não o Gabarito. Decidir se entra no Glossário. Se entrar, o #26 vai para A: 22/26 (85%) e 24/26 (92%).
- **#20 e `remover_mascara`.** O SQL remove todo caractere não numérico. Definir na spec do Catálogo se `remover_mascara` cobre isso ou só a máscara de identificadores.
- **Conferir no código** as condições classificadas só pela transformação do inventário: todas exceto #8, #10 e #18.
- **Fora deste repositório.** No `data-application-mir`, `airflow_lappis/dags/dbt/mir/models/empenhos_ted_dbt/silver/schema.yml:311` ainda fala em "9 métodos sequenciais de extração via regex"; são 16 passos.
