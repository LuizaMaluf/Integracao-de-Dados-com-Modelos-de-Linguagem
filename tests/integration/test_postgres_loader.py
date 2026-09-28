import pandas as pd
import pytest

from govhub.integration.loaders.postgres_loader import (
    PostgresLoader,
    is_pg_source,
    parse_source,
)
from govhub.sync.silver_sync import sync_dataframe


@pytest.mark.parametrize("source, esperado", [
    ("pg://silver.ibge_municipios", ("silver", "ibge_municipios")),
    ("bronze.ibge", ("bronze", "ibge")),
    ("ibge", ("silver", "ibge")),
])
def test_parse_source(source, esperado):
    assert parse_source(source) == esperado


@pytest.mark.parametrize("source", ["pg://silver.x;drop", "pg://Silver.X", "pg://a.b.c"])
def test_parse_source_rejeita_nomes_invalidos(source):
    with pytest.raises(ValueError):
        parse_source(source)


def test_is_pg_source():
    assert is_pg_source("pg://silver.x")
    assert not is_pg_source("data/raw/x.csv")


@pytest.mark.pg
def test_load_remove_linhagem_e_monta_metadata(pg_engine, pg_schema):
    df = pd.DataFrame({"cd_ibge": [5300108, 5208707], "nome": ["Brasília", "Goiânia"]})
    sync_dataframe(df, "municipios", "municipios_20260928", schema=pg_schema, engine=pg_engine)

    out, meta = PostgresLoader(engine=pg_engine).load(f"pg://{pg_schema}.municipios")
    assert list(out.columns) == ["cd_ibge", "nome"]
    assert meta.name == f"{pg_schema}.municipios"
    assert meta.row_count == 2 and len(meta.sample) == 2

    com_linhagem, _ = PostgresLoader(engine=pg_engine).load(
        f"{pg_schema}.municipios", drop_lineage=False
    )
    assert {"dt_ingest", "_silver_table"} <= set(com_linhagem.columns)
