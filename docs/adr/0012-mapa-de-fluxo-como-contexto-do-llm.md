# ADR 0012 — Mapa de Fluxo como contexto do LLM

**Status:** Proposto

## Contexto

O inventário das bases do Gov Hub (`docs/tcc/inventario-govhub.md`) mostrou que os joins reais mais difíceis extraem a chave de texto livre: o número do TED vem de dentro de `ne_ccor_descricao`, o número do convênio vem do texto da NE, o `info_complementar` carrega UG, modalidade e número do contrato. Nenhuma dessas chaves cabe no Catálogo de Transformações (ADR 0011), e um analista só as enxerga porque conhece o fluxo da política: um TED gera uma NC, depois uma PF, depois uma NE, e a norma manda anotar o número do TED na NE. No artigo-base, esse conhecimento implícito é o que a documentação dos silos entrega ao LLM. Com o MinC como domínio de aplicação (ADR 0014), o mesmo vale para a política cultural: um número de PRONAC ou um plano de ação do TransfereGov só aparece em outra base porque a política manda carregá-lo.

## Decisão

1. O Domain Context passa a ter dois artefatos: o **Glossário** (sinônimos de coluna e padrões de identificador, o que já existe) e o **Mapa de Fluxo**: a descrição, em nível de documento, do processo da política — quais documentos existem, qual sistema registra cada um, qual o formato do identificador de cada um e onde o identificador de um documento é carregado no registro de outro, com a norma que sustenta cada elo.
2. O Mapa é escrito pela autora a partir de normas e manuais públicos e do conhecimento do time do Gov Hub; descreve documentos e elos, nunca condições de join; é revisado por alguém do MinC (nome em aberto) e congelado com o Conjunto de Teste. Cada formato de identificador do Mapa cita uma fonte pública (norma ou manual oficial).
   - **Escopo do Mapa no MinC:** o PRONAC (proposta → projeto → captação → execução), a LPG/PNAB fundo a fundo (TransfereGov → plano de ação → conta no BB Ágil → pagamento ao agente) e a parte TED/NE do SIAFI, que vale para qualquer ministério. Fontes candidatas, a confirmar: Lei 8.313/1991, LC 195/2022 e Lei 14.399/2022.
3. O LLM recebe o Mapa como contexto e **nomeia** o que uma coluna carrega ("`ne_ccor_descricao` carrega um número de TED"); a extração é feita por um estágio determinístico com a operação `extrair_identificador(tipo)` do Catálogo. O padrão de cada tipo é derivado do formato do identificador no Mapa congelado, nunca do SQL de produção. O LLM nunca escreve regex.
4. A ablação do Domain Context ganha três níveis: sem contexto, só Glossário, Glossário + Mapa de Fluxo. Nos pares com atrito de texto livre entra uma condição a mais: `extrair_identificador` disponível com padrão genérico (os padrões de identificador do Glossário), sem o Mapa. Ela separa o efeito de ter a operação do efeito de o LLM saber o que a coluna carrega.

## Alternativas rejeitadas

- **Deixar o LLM devolver o regex de extração:** regex é quase código executado; contradiz a ADR 0011 e não é validável contra o domínio.
- **Ampliar o Catálogo com operações ad hoc de texto** (`substring_apos`, `entre_delimitadores`…): resolve o caso a caso sem dar ao LLM o motivo de a chave estar ali; não generaliza para pares novos. A ADR 0013 aceita só o delimitador literal posicional dentro de `trecho`, que não busca padrão no texto.
- **Aceitar a Abstenção nesses pares:** honesto, mas descarta justamente os pares mais ricos do domínio e não testa a hipótese de que o contexto do fluxo é o que falta ao LLM.

## Consequências

- O Mapa de Fluxo é uma contribuição independente do pipeline, reutilizável pelo Gov Hub; portar o método para outro domínio é escrever outro Mapa (paralelo com o "um dia para outro fabricante" do artigo-base).
- Risco de vazamento: a autora escreve o Mapa e conhece os gabaritos. Mitigação: cada formato e cada elo citam uma fonte pública, os padrões de extração saem dos formatos e não do SQL de produção, o Mapa não contém joins e é revisado antes do congelamento.
- Cascatas de fallback e predicados de filtro dos joins reais ficam fora do artefato: o Gabarito registra as etapas da cascata como Chaves Aceitáveis (a primeira como principal) e os filtros como escopo do par. A cascata completa fica fora do escopo; como medida secundária, relatada à parte, a avaliação mede o recall da chave escolhida contra o join da cascata inteira.
