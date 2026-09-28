{{
  config(materialized='table')
}}

select
    ne.num_empenho,
    ne.ano_empenho,
    ne.valor_empenho,
    ne.nome_favorecido,
    ne.ug_emitente,
    ne.dt_emissao,
    ne.dt_ingest,
    pf.ptres,
    pf.fonte_recurso,
    pf.natureza_despesa
from {{ ref('siafi_notas_empenho') }} ne
left join {{ source('silver', 'siafi_programacao_financeira') }} pf
    on ne.ug_emitente = pf.ug
   and ne.ano_empenho = pf.ano
