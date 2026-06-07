{{
  config(
    materialized='incremental',
    unique_key='num_empenho',
    on_schema_change='sync_all_columns'
  )
}}

select *
from {{ source('silver', 'siafi_notas_empenho') }}

{% if is_incremental() %}
  where dt_ingest > (select max(dt_ingest) from {{ this }})
{% endif %}
