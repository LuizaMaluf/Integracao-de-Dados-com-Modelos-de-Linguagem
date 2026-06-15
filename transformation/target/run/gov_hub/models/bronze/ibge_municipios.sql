
      insert into "govhub"."bronze"."ibge_municipios" ("id", "nome", "microrregiao", "regiao_imediata")
    (
        select "id", "nome", "microrregiao", "regiao_imediata"
        from "ibge_municipios__dbt_tmp142125719323"
    )


  