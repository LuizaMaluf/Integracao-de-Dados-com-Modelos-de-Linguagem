# Inventário das bases do GovHub

Levantamento de 2026-10-03 nos repositórios `data-application-*` da organização GovHub-br, feito para montar o ground truth (Pares Reais), escolher os pares da QP4 e as tabelas-semente dos Pares Perturbados. Caminhos de dbt são relativos a `airflow_lappis/dags/dbt/` (gov-hub, cidades, mir) ou à raiz (minc). Conferir no código antes de anotar um Gabarito: este inventário foi feito por leitura estática, sem rodar nada.

| Repositório | Órgão | Último commit | Observação |
| --- | --- | --- | --- |
| `data-application-gov-hub` | IPEA (projetos `ipea` e `mir`) | 2026-07-27 | Local em `~/Developer/projects/govhub/` |
| `data-application-cidades` | MCID | 2026-08-13 (branch `chore/reanalise-acervo`) | Local; copia as DAGs e os dbt do gov-hub |
| `data-application-minc` | MinC | 2026-09-22 | Local |
| `data-application-mir` | MIR | 2026-10-02 | Só no GitHub; versão mais recente dos models `mir` |
| `data-application-mgi` | MGI | 2026-09-03 | Só no GitHub; só ingestão, nenhum model dbt |

## Fontes ingeridas

| Fonte | Como chega | Schema no PostgreSQL | Repositórios |
| --- | --- | --- | --- |
| Compras.gov (API de contratos) | REST | `compras_gov.{contratos, empenhos, faturas, cronograma, terceirizados}` | gov-hub, cidades, mir |
| Compras.gov Dados Abertos (catálogo, UASG, contratações 14.133, ARP, PGC) | REST | `compras_gov.raw_*` (28 tabelas) | mgi |
| SIAFI (API Serpro) | REST | `siafi.{notas_empenho, nota_credito, programacao_financeira_siafi}` — nenhum model lê | gov-hub |
| Tesouro Gerencial (relatórios do SIAFI) | CSV por e-mail | `siafi.{ne_tesouro, nc_tesouro_*, pf_tesouro, empenhos_tesouro, programacao_acao_ptres, …}` | gov-hub, cidades, mir |
| TransfereGov TED | REST | `transfere_gov.{programas, planos_acao, notas_de_credito, programacao_financeira}` | gov-hub, cidades, mir |
| TransfereGov Transferências Especiais | REST | `transferegov_emendas.*` (12 tabelas) | gov-hub, mir |
| TransfereGov Fundo a Fundo | REST | `transferegov.{programa_minc, plano_acao_minc, plano_acao_dado_bancario_minc, relatorios_gestao, …}` | minc |
| SICONV | zip/CSV (dados.gov.br) | `siconv.*` (16 tabelas) | gov-hub, mir |
| PNCP | REST | `pncp.contratacoes_*` — nenhum model lê | gov-hub |
| SIAPE | SOAP (Conecta) | `siape.{dados_pessoais, dados_funcionais, dados_financeiros, dados_uorg, …}` | gov-hub, cidades |
| SIORG | REST | `siorg.{unidade_organizacional, estrutura_organizacional_cargos, cargos_funcao}` | gov-hub, cidades |
| Câmara e Senado (dados abertos) | REST | `camara_deputados.*`, `senado_federal.*` | gov-hub, mir |
| PPA / SIOP | CSV | `ppa.*` (31 tabelas) | mir |
| IBGE (censo em xlsx; SIDRA; FCU 2022; localidades) | FTP / REST / CSV | `censo_demografico.*`, `ibge.*`, `ibge_sidra.*`, `transferegov.territorio_fcu_setores`, `__dados_brutos.api_ibge_{uf,regioes,municipios}` | gov-hub, cidades, minc |
| SALIC | SQL Server | `salic_bronze.*` (571 tabelas) | minc |
| BB Gestão Ágil | REST (Serpro) | `bbagil.{extrato_bbagil, subtransacao_bbagil}` | minc |
| Ancine | planilha | `ancine.{consulta, tabela}` | minc |
| SICONFI, Bacen SGS, Mapas Culturais | REST | `siconfi_bronze.*`, `bacen.*`, `dados_mapa_cultura.*` | minc, cidades |
| MCMV (GFAR, CAIXA, SNH) | SFTP | `sftp` / `__dados_brutos.novo_mcmv_*`, `dados_prioritarios_recebidos_caixa_*` | cidades |
| FGV, FIPE, ABECIP, InfoMoney, MRV, CAGED | REST / xlsx | `fgv.*`, `fipe.*`, `abecip.*`, `infomoney.*`, `mrv.*`, `novo_caged.*` | cidades |
| Sisbolsas, IPEA Pro, SGAC | cópia de SQL Server; CSV por e-mail | `sisbolsas.*`, `ipea_pro.*`, `sgac.projetos_sgac` | gov-hub |

## Joins entre fontes já em produção (candidatos a Pares Reais)

A condição de join e a transformação usadas em produção são o Gabarito. A coluna "Categoria" é a classificação preliminar por Categoria de Atrito (`CONTEXT.md`).

### SIAFI / Tesouro Gerencial × Compras.gov

| # | Model | Condição | Transformação | Categoria |
| --- | --- | --- | --- | --- |
| 1 | `ipea/models/contratos_dbt/silver/contratos_empenhos.sql:30-33` (mir: `contratos_dbt/silver/contratos_empenhos.sql:35-37`) | `c.ne = e.ne_transformed and c.cnpj_cpf = e.ne_ccor_favorecido` | `upper(right(ne_ccor,12))`; `regexp_replace(cnpj,'[/.-]','')` | Formato de identificador (NE curta × SIAFI Identifier); chave composta |
| 2 | mesmo arquivo, fallbacks `:84`, `:128`, `:170` | `num_processo`; só CNPJ; `info_complementar` | processo sem pontuação; `concat(UG, modalidade, numero)` × `substring(ne_info_complementar from '^([0-9]+) -')` | Derived Key; extração de texto livre |
| 3 | `contratos_dbt/silver/contratos_estagios.sql:27/59/89` | `using (ne, cnpj_cpf)` → `(cnpj_cpf, num_processo)` → `(cnpj_cpf, info_complementar)` | idem | idem |
| 4 | `contratos_dbt/gold/contratos_comparativo_mensal.sql:25` | `using (contrato_id, mes_ref)` | `to_date(split_part(emissao…))` × `to_date(ano||'-'||mes||'-01')` | Formato (data); Derived Key |
| 5 | mir `contratos_dbt/bronze/empenhos_tesouro.sql:53-56` | `ne_ccor in (select unidade_gestora || gestao || upper(numero) from compras_gov.empenhos)` | concatenação UG + gestão + NE | Derived Key (o exemplo do `CONTEXT.md`) |

### Tesouro Gerencial × TransfereGov TED

| # | Model | Condição | Transformação | Categoria |
| --- | --- | --- | --- | --- |
| 6 | `ipea/models/ted_dbt/views/num_transf_n_plano_acao.sql:21` (mir: `empenhos_ted_dbt/views/…:21`) | `using (nc, ug)` com `tx_numero_nota`, `cd_ug_emitente_nota` | `left(nc,6) as ug, right(nc,12) as nc` | Derived Key (decompõe o SIAFI Identifier); composta |
| 7 | `ted_dbt/silver/pf_plano_acao.sql:43`; mir `silver/pf_unificado.sql:73` | `using (pf, ug_emitente)`; `using (pf_chave)` | `right(pf,12)`; `upper(trim(right(pf,12)))` × `upper(trim(tx_numero_programacao))` | Formato de identificador |
| 8 | `ted_dbt/silver/empenhos_plano_acao.sql:31`; mir `silver/empenhos_por_plano_acao.sql:442-443` | `using (num_transf)`; `er.num_transf = cast(pa.num_transf as text)` | `num_transf` extraído por regex de `ne_ccor_descricao` (9 métodos em cascata); ano de 2 dígitos expandido por CASE | Extração de texto livre; Equivalência lógica |
| 9 | `ted_dbt/silver/nc_plano_acao.sql:31`; mir `:21` | `nc_transferencia = pda.num_transf` | — | Grafia/nomenclatura |
| 10 | `ted_dbt/gold/ted_resumo_orcamentario.sql:115`; mir `gold/…:149, 204-207` | `using (plano_acao)`; `using (plano_acao, num_transf)` | `ltrim(trim(cast(x as text)),'0')` | Formato (zeros à esquerda); composta |
| 11 | `ted_dbt/silver/bolsistas_nc_tesouro.sql:50-52`; mir `silver/nc_unificado.sql:67` | `fonte_recursos_codigo = nc_fonte_recursos and ptres = ptres`; `trim(ptres) = trim(ptres)` | `split_part(ptres,'.',1)` | Formato; composta (dois relatórios do Tesouro) |

### SIAFI × SICONV / emendas × Câmara e Senado

| # | Model | Condição | Transformação | Categoria |
| --- | --- | --- | --- | --- |
| 12 | `siconv_dbt/silver/emendas_convenio.sql:126-127` (mir `:129-130`); `emendas_dbt/silver/instrumentos_emendas.sql:83-84` | `e.numero_transferencia = c.nr_convenio`; `::text = pa.sq_instrumento` | número extraído por regex do texto da NE, `::integer` | Extração de texto livre; Formato |
| 13 | `siconv_dbt/silver/convenios_consolidados.sql:20-23` (mir `:38-39`) | `cast(nr_convenio as text) = ne_info_complementar` | filtro `left(ne_ccor,6)='810008'` | Formato (tipo); predicado de filtro |
| 14 | `mir/models/emendas_dbt/silver/emendas_partidos.sql:93-94` (mir repo `:136-137`) | `e.chave_join_nome = p.chave_join_nome` | `TRIM(TRANSLATE(UPPER(x),'ÁÀ…','AA…'))`; `initcap(trim(regexp_replace(split_part(autor,'/',1),'\s+',' ')))`; desempate por data de filiação | Grafia/nomenclatura (nome de parlamentar) |
| 15 | `emendas_dbt/silver/planos_partidos.sql:92-93` | nome × nome | `TRIM(UPPER(nome))` | Grafia/nomenclatura |
| 16 | `dados_abertos_dbt/bronze/deputados_historico.sql:45-46` | `dr.id_legislatura = ld.id` | `::integer` | Formato (tipo) |

### SIAPE × SIORG (atenção: dados pessoais)

| # | Model | Condição | Transformação | Categoria |
| --- | --- | --- | --- | --- |
| 17 | `ipea/models/pessoas_dbt/silver/unidades_organizacionais_siorg_siape.sql:50` | `a.sigla_uorg = uo.sigla_unidade` | CASE `'GABIN-IPEA'→'GABIN'` | Equivalência lógica |
| 18 | `silver/tabela_correlacao_cargos.sql:70-72`; `quantitativo_alocados_ocupados.sql:86-89`; `gold/hierarquia.sql:63-65` | `codigo_combinacao_siorg = codigo_combinacao_siape and siglaunidade = sigla_uorg_exercicio` | `substring(x,1,1)||substring(x,length(x)-2,3)`; `replace(funcao,' ','')` | Derived Key; composta |
| 19 | `gold/cargos_consolidado.sql:32-33` | `siape.cpf = siorg.cpf_titular` | CPF só dígitos de um lado; JSON bruto do outro | Formato; Estrutura aninhada — **chave é CPF** |

### Outros

| # | Repositório / model | Condição | Transformação | Categoria |
| --- | --- | --- | --- | --- |
| 20 | gov-hub `sistema_sisbolsas/silver/sgac_teds_siafi.sql:149-151` (SGAC × Tesouro) | `s.siafi_norm = t.transf_norm`, `length >= 5` | `regexp_replace(coalesce(x,''),'[^0-9]','')` | Formato |
| 21 | gov-hub `chamadas_publicas.sql:374`; `bolsistas.sql:127` (Sisbolsas × IPEA Pro) | `c.co_projeto = proj.projetoid::text` | cast | Formato (tipo) |
| 22 | cidades `mcid/models/empreendimento_far_dbt/silver/empreendimento.sql:82-84` (GFAR × CAIXA) | `id_proposta`; `c.apf = o.apf` | UDF `normalize_apf`: `lpad(replace(x,'-',''),8,'0')` | Formato (zeros, máscara) |
| 23 | cidades `evolucao_financeira.sql:76-77`; `fds_empreendimento.sql:190-193` | `m.apf_raiz = left(e.apf, 6)` | `right(apf,6)` × `left(apf,6)` | Derived Key |
| 24 | cidades `gold/mapa_nacional.sql:41`, `panorama_estadual.sql:165…` (MCMV × IBGE UF) | `f.uf = i.sigla` | `nullif(trim(sg_uf),'')` | Grafia |
| 25 | cidades `conjuntura_dbt/silver/silver_financiamentos_habitacionais.sql:48-50`; `gold_ticket_medio_vs_incc.sql:47-49` | `on (ano, trimestre)` | trimestre derivado de `EXTRACT(MONTH)` por CASE | Derived Key; composta |
| 26 | minc `cotas_dbt/gold/fct_pagamentos_elegiveis.sql:46-47` (planilhas TransfereGov × IBGE FCU) | `chave_municipio_uf = chave_municipio_uf` | `sem_acento(cidade)||'|'||sem_acento(uf)` × `sem_acento(nm_mun)||'|'||lower(sigla_uf)`, com código de UF → sigla por tabela CASE | Derived Key; Equivalência lógica; Grafia |
| 27 | minc `agentes_dbt/gold/primeiro_acesso_anual.sql:66-69` (BB Ágil ∪ SALIC ∪ Ancine) | `beneficiario_documento` + `programa_fomento` + `ano` | `LPAD(REGEXP_REPLACE(doc,'[^0-9]',''), 11|14, '0')`, 11 ou 14 por tipo de pessoa | Formato (máscara, zeros); **CPF** |
| 28 | minc `cotas_dbt/gold/fct_pagamentos_bbagil.sql:37-41` (model desativado) | `ente_bbagil = id_plano_acao::text`; `identificador_unico` | só dígitos | Formato |
| 29 | minc `extracao_bbagil_dag.py:94-99` (TransfereGov → BB Ágil, na ingestão) | `agencia`, `conta` | `int()` descarta zeros à esquerda | Formato (zeros) |

Joins dentro de uma mesma fonte com transformação, úteis como semente: SALIC PRONAC = `lpad(trim(ano),2,'0')||trim(sequencial)` (minc `macros/salic/chaves_salic.sql:40-47`); SIAPE `right(codigo_orgao_uorg,7)::integer = cast(codigo as int)`; SIORG `regexp_replace(x,'^.*/','')` em códigos de unidade.

## Pares ainda não integrados (candidatos à QP4)

| Par | Onde | Observação |
| --- | --- | --- |
| PNCP × `compras_gov.contratos` | gov-hub | PNCP ingerido, nenhum model lê |
| SIAFI API (`siafi.notas_empenho`) × Tesouro Gerencial (`siafi.ne_tesouro`) | gov-hub | Mesmo documento por dois caminhos; nenhum model usa a API |
| `siconv.proposta.cod_munic_ibge` × IBGE municípios | gov-hub, mir | — |
| MCMV `cod_ibge` × `api_ibge_municipios` | cidades | `api_ibge_municipios` e `api_ibge_regioes` declarados e nunca usados |
| Ancine `consulta."No SALIC"` × SALIC PRONAC | minc | — |
| SALIC código IBGE de 6 dígitos × `cod_ibge` de 7 dígitos (TransfereGov, BB Ágil) | minc | A ponte 6↔7 existe em `agentes__populacaomunicipio` |
| SICONFI e IBGE SIDRA × `territorio_fcu.cd_mun` | minc | — |
| PPA `programa` × SIAFI `programa_governo` | mir | — |
| `compras_gov` (API de contratos, MIR) × `compras_gov` (Dados Abertos, MGI) | mir, mgi | Dois schemas homônimos de APIs diferentes, sem ligação |
| FKs documentadas e não implementadas do MGI (`idcompra` → `raw_contratacoes`; `codigoorgao` → `raw_orgao`; contratos × itens em `(codigounidadegestora, numerocontrato, nifornecedor)`) | mgi `documentacao-schema-compras-gov.md:44-260, 300-652` | Gabarito documentado, join inexistente — categoria intermediária |

## Dados pessoais (LGPD)

- **SIAPE** (`dados_pessoais`, `dados_funcionais`, `dados_financeiros`, `dados_dependentes`, `dados_pa`): CPF, nome, filiação, raça/cor, deficiência, salários, conta bancária.
- **SIORG** `cpf_titular`, `nome_titular`.
- **Compras.gov** `terceirizados`: CPF, nome, salário.
- **Tesouro Gerencial** `pagamentos_ob_bolsa` e `ne_ccor_favorecido` quando o favorecido é pessoa física.
- **Sisbolsas** `tb_dado_pessoal`, `tb_dado_bancario`; **BB Ágil** `beneficiarydocumentid`/`name` (~176 mil CPFs); planilhas do MinC com raça e PcD (dados sensíveis); **SALIC** `cgccpf`, agentes físicos; **SICONV** `identif_fornecedor`.
- Já tagueado como `PII.Sensitive` nos `schema.yml` do minc (`scripts/classificar_pii.py`).

## Observações para o desenho da avaliação

1. **Transformações além do Catálogo.** Vários Gabaritos reais extraem a chave de texto livre por regex (`num_transf` de `ne_ccor_descricao`, `numero_transferencia` do texto da NE, `info_complementar`), ou usam cascatas de fallback e desempate por data. O Catálogo de Transformações atual (8 operações) não expressa isso.
2. **Predicados de filtro no join.** `left(ne_ccor,6)='810008'` e a janela por Exercício fazem parte da chave em produção.
3. **Decomposição do SIAFI Identifier** (`left(nc,6)` = UG, `right(nc,12)` = documento) aparece em pelo menos cinco models: é a Derived Key mais frequente do domínio.
4. **Nome de pessoa como chave** (parlamentares) é o único caso de Grafia/nomenclatura em valores, não em nomes de coluna.
