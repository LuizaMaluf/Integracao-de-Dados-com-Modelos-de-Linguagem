{{
  config(materialized='table')
}}

select
    ne.ano_empenho                          as ano,
    ne.ug_emitente                          as ug,
    ne.ptres,
    ne.fonte_recurso,
    count(distinct ne.num_empenho)          as qtd_empenhos,
    sum(ne.valor_empenho)                   as total_empenhado,
    count(distinct pa.id_plano_acao)        as qtd_planos_acao
from {{ ref('siafi_empenhos_enriched') }} ne
left join {{ source('silver', 'transfere_gov_planos_acao') }} pa
    on ne.num_empenho = pa.num_empenho  -- chave identificada pelo IntegrationAgent
group by 1, 2, 3, 4
