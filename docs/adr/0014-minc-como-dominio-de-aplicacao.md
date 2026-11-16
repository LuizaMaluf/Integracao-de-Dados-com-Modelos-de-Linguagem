# ADR 0014 — MinC como domínio de aplicação

**Status:** Proposto

## Contexto

O pôster do CAIN 2027 foi escrito com o MIR como contexto: a cascata do #8 e boa parte das versões dos joins do inventário (`docs/tcc/inventario-govhub.md`) vêm do `data-application-mir`. O TCC passa a aplicar o método no MinC (`data-application-minc`). O levantamento do repositório do MinC mostrou que ele sozinho não fecha o benchmark: há poucos joins ativos entre fontes diferentes, e quase todos têm chave em CPF/CNPJ.

- **Joins ativos entre fontes**: o #26 (planilhas TransfereGov × IBGE FCU por município e UF), o #27 (BB Ágil, SALIC e Ancine por documento; a normalização do documento fica no UNION de `int_ancine_bbagil_salic.sql`) e o #29 (agência e conta na DAG do BB Ágil).
- **Joins desativados**: com chave em CPF/CNPJ, como o #28.
- **Pares documentados sem join**: Ancine `no_salic` → PRONAC; código de município do SALIC (6 dígitos) ↔ código IBGE (7 dígitos); BB Ágil `cod_ibge`/`id_plano_acao` → TransfereGov; MUNIC × SALIC; Mapas Culturais × IBGE; SICONFI × IBGE.

## Decisão

1. **Pares Reais.** Continuam vindo de todo o Gov Hub. Quando a mesma condição existe no `data-application-gov-hub` e no `data-application-mir`, o Gabarito usa a versão do `data-application-gov-hub`.
2. **MinC como domínio de aplicação.** O Mapa de Fluxo (ADR 0012), a QP3, a QP4 e as tabelas-semente dos Pares Perturbados passam a vir do MinC.
3. **CPF/CNPJ no MinC.** Vale a mesma regra do #1–#3: o escopo do par fica restrito a pessoa jurídica (CNPJ de 14 dígitos). O #27 entra no ground truth com esse escopo.
4. **Só joins ativos.** Joins desativados não entram nos Pares Reais; o #28 continua excluído.
5. **QP4.** Os pares candidatos passam a ser os pares documentados sem join do MinC, listados no Contexto.
6. **Pôster.** O artigo do CAIN 2027 fica como foi submetido; os números dele descrevem o inventário na submissão. A troca é registrada só no TCC.

## Alternativas rejeitadas

- **Só o MinC** (Pares Reais, Mapa, QP4 e sementes só do MinC): sobram poucos pares sem CPF para o ground truth, e o camera-ready teria de mudar.
- **Manter a exclusão de todo par com CPF/CNPJ no MinC:** sobraria só o #26 entre os joins do MinC.
- **Pseudonimizar o documento com HMAC:** muda o valor da chave e esconde o atrito de formato que o par deveria medir; o próprio MinC ainda não aplica o HMAC.
- **Incluir os joins desativados, como já se fez com o #28:** um join desativado não é produção, e o Gabarito deixa de ser o que o Gov Hub roda.

## Consequências

- O inventário e a cobertura do Catálogo (ADR 0013) são recontados com as versões do `data-application-gov-hub` e com o #27 dentro do universo.
- A cascata de 16 passos do #8 é do `data-application-mir`; sai da contagem e fica num anexo que descreve o estado do pôster.
- O Mapa de Fluxo precisa de um revisor do MinC, e as tabelas-semente precisam estar no PostgreSQL acessível; os dois ficam em aberto na proposta.
