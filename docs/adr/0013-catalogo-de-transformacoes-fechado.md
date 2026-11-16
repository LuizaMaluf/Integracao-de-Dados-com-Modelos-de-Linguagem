# ADR 0013 — Catálogo de Transformações fechado

**Status:** Proposto

## Contexto

A ADR 0011 fixou um Catálogo de Transformações com nove operações e até três operações por lado, mas não definiu os parâmetros de cada uma. O inventário (`docs/tcc/inventario-govhub.md`) tem 29 condições de join entre fontes; três ficam fora do benchmark por terem chave em CPF (#19, #27 e #28), restando 26. Contra o rascunho do catálogo (`docs/tcc/cobertura-catalogo.md`), 14 das 26 cabem em até três operações por lado (54%), 18 cabem se a extração por `extrair_identificador(tipo)` contar (69%) e 8 dependem de definições ainda abertas. Esta ADR fecha essas definições antes do congelamento. Depois dela, a ADR 0014 trouxe o #27 para o universo, com escopo restrito a pessoa jurídica, e o universo passou a 27 condições.

## Decisão

1. **Operações e parâmetros.** Cada operação tem um template SQL fixo e um teste unitário; o LLM escolhe a operação e os parâmetros listados, nada mais.

   | Operação | Parâmetros | Cobre |
   | --- | --- | --- |
   | `converter_tipo` | tipo de destino | casts (`::text`, `::integer`) |
   | `normalizar_texto` | opções fixas: caixa, espaços, remoção de acentos | `upper`, `trim`, `translate` de acentos (#14, #26) |
   | `remover_mascara` | — | retirar `.`, `/`, `-` e espaços de identificadores |
   | `preencher_zeros` | largura (obrigatória) | `lpad` com zeros; remover zeros à esquerda (#10) se expressa como `preencher_zeros` nos dois lados com a mesma largura |
   | `trecho` | posição inicial e tamanho, a partir do início ou do fim; **ou** delimitador literal e índice da parte | `left`, `right`, `substring` posicional, `split_part` (#4, #11) |
   | `concatenar` | argumentos (colunas, literais ou `trecho`) e separador opcional | `\|\|`, `concat` (#5, #18) |
   | `mapear_valores` | pares de valores, só do Glossário (ADR 0011) | de-para de códigos |
   | `converter_data` | formato de origem; granularidade em {dia, mês, trimestre, ano} | `to_date`, truncar para o mês (#4), derivar trimestre (#25) |
   | `extrair_identificador` | tipo de identificador do Mapa de Fluxo | número de TED, convênio ou NE em texto livre (ADR 0012) |

2. **Limite de operações.** Até três operações por lado da chave, como no artigo do CAIN 2027. Cada `trecho` usado como argumento de `concatenar` conta no limite.
3. **Checagem da largura.** A validação reprova um `preencher_zeros` se o perfil da coluna tiver valor mais longo que a largura declarada.
4. **Fora do catálogo.** Viram Abstenção, contada como "transformação fora do catálogo":
   - extração por busca de padrão no texto (`substring_apos`, `entre_delimitadores`, regex escrito pelo LLM), rejeitada na ADR 0012;
   - de-para cujos pares não estão no Glossário, como o `CASE 'GABIN-IPEA' → 'GABIN'` do #17 (pôr o par no Glossário copiaria o Gabarito);
   - sequências com mais de três operações num lado.
5. **Desempate por data.** O desempate do #14 (filiação partidária vigente na data) fica fora do catálogo e fora do escopo do par, porque depende da linha de A e não é um filtro por tabela. A Chave Aceitável é a do nome, e o Join de Referência é calculado sem desempate, anotado no Gabarito.
6. **Classe de uma cascata.** Cada etapa de uma cascata é uma Chave Aceitável e a primeira é a principal; a classe de cobertura do par segue a primeira etapa.

## Cobertura resultante

Recontagem das 27 condições do universo da ADR 0014 com as definições acima, detalhada em `docs/tcc/cobertura-catalogo.md`:

- **22/27 (81%)** cabem sem `extrair_identificador`;
- **24/27 (89%)** cabem contando as 2 que precisam de `extrair_identificador` na primeira etapa (#8 e #12);
- **3/27 (11%)** ficam fora e viram Abstenção: #17 (de-para fora do Glossário), #18 e #26 (mais de três operações num lado).

Com a regra do artigo, que põe na classe B toda condição com `extrair_identificador` em alguma etapa, são 20/27 (74%) sem extração e 24/27 (89%) com ela. Das 8 condições que dependiam de definição, 5 cabem (#4, #10, #11, #14 e #25) e 3 ficam fora. No universo de 26 do pôster, as mesmas definições davam 21/26 (81%) e 23/26 (88%).

A contagem descreve ajuste, não generalização: o catálogo saiu do mesmo inventário de onde vêm os Pares Reais. Os Pares Reais medem a escolha da chave, e a generalização fica com a QP4.

## Alternativas rejeitadas

- **Operação `remover_zeros` própria:** duplica `preencher_zeros` nos dois lados e abre um caso em que valores de larguras diferentes passam a casar sem checagem.
- **Limite de três operações por coluna da chave:** cabe mais pares, mas diverge da regra publicada no artigo e da contagem feita com ela.
- **`mapear_valores` com pares observados nas duas colunas:** deixa o LLM casar dois valores quaisquer só porque existem, o que é inventar equivalência por outra porta.
- **Delimitador por padrão (`substring_apos`, `entre_delimitadores`):** ver ADR 0012. O delimitador literal de `trecho` só divide o valor numa posição estrutural, como `left` e `right`.

## Consequências

- O catálogo é versionado e congelado com o Conjunto de Teste; cada operação ganha template SQL e teste unitário na spec do Catálogo.
- A avaliação conta as Abstenções por transformação fora do catálogo separadamente das demais.
