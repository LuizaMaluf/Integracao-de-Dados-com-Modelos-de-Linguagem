-- GERADO por govhub.sync.dbt_source_generator a partir de ibge_estados.yaml. NÃO editar à mão.
{{
  config(
    materialized='incremental',
    incremental_strategy='delete+insert',
    unique_key='_silver_table',
    on_schema_change='append_new_columns'
  )
}}

select *
from {{ source('registry', 'ibge_estados') }}

{% if is_incremental() %}
  where dt_ingest > (select coalesce(max(dt_ingest), '1900-01-01'::timestamptz) from {{ this }})
{% endif %}
