-- Model bronze ESCRITO À MÃO para a fonte IBGE (config-driven não cobre esta camada)
select * from {{ source('silver_poc', 'ibge_municipios') }}
