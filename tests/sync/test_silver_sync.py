import json

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import text

from govhub.sync import silver_sync


def test_flatten_structs_serializa_dict_list_e_array():
    df = pd.DataFrame({
        "id": [1, 2],
        "uf": [{"sigla": "DF", "regiao": {"nome": "Centro-Oeste"}}, {"sigla": "GO"}],
        "tags": [["a", "b"], np.array(["c"])],
        "nome": ["Brasília", "Goiânia"],
    })
    out = silver_sync.flatten_structs(df)

    assert json.loads(out.loc[0, "uf"])["regiao"]["nome"] == "Centro-Oeste"
    assert json.loads(out.loc[1, "tags"]) == ["c"]
    assert out["nome"].tolist() == ["Brasília", "Goiânia"]  # texto simples intacto
    assert out["id"].tolist() == [1, 2]
    assert isinstance(df.loc[0, "uf"], dict)  # não altera o DataFrame original


def test_airflow_task_usa_target_table_do_registry(monkeypatch):
    chamadas = []
    monkeypatch.setattr(
        silver_sync, "sync_to_postgres", lambda lote, destino: chamadas.append((lote, destino)) or 3
    )
    cfg = {"source_name": "IBGE Municípios", "target_table": "ibge_municipios"}
    assert silver_sync.airflow_task(cfg, "ibge_municipios_20260928") == 3
    assert chamadas == [("ibge_municipios_20260928", "ibge_municipios")]


def _rows(engine, schema, table):
    with engine.connect() as conn:
        return pd.read_sql(text(f'select * from "{schema}"."{table}" order by id'), conn)


@pytest.mark.pg
def test_sync_cria_tabela_com_linhagem(pg_engine, pg_schema):
    df = pd.DataFrame({"id": [1, 2], "uf": [{"sigla": "DF"}, {"sigla": "GO"}]})
    n = silver_sync.sync_dataframe(df, "municipios", "municipios_20260928",
                                   schema=pg_schema, engine=pg_engine)
    assert n == 2
    out = _rows(pg_engine, pg_schema, "municipios")
    assert set(silver_sync.LINEAGE_COLUMNS) <= set(out.columns)
    assert out["_silver_table"].unique().tolist() == ["municipios_20260928"]
    assert json.loads(out.loc[0, "uf"]) == {"sigla": "DF"}


@pytest.mark.pg
def test_sync_mesmo_lote_e_idempotente_e_lotes_diferentes_acumulam(pg_engine, pg_schema):
    df = pd.DataFrame({"id": [1, 2]})
    for _ in range(2):
        silver_sync.sync_dataframe(df, "t", "t_20260927", schema=pg_schema, engine=pg_engine)
    assert len(_rows(pg_engine, pg_schema, "t")) == 2

    silver_sync.sync_dataframe(df, "t", "t_20260928", schema=pg_schema, engine=pg_engine)
    out = _rows(pg_engine, pg_schema, "t")
    assert len(out) == 4
    assert sorted(out["_silver_table"].unique()) == ["t_20260927", "t_20260928"]


@pytest.mark.pg
def test_sync_adiciona_coluna_nova_da_fonte(pg_engine, pg_schema):
    silver_sync.sync_dataframe(pd.DataFrame({"id": [1]}), "t", "t_1",
                               schema=pg_schema, engine=pg_engine)
    silver_sync.sync_dataframe(pd.DataFrame({"id": [2], "nova": [42]}), "t", "t_2",
                               schema=pg_schema, engine=pg_engine)
    out = _rows(pg_engine, pg_schema, "t")
    assert pd.isna(out.loc[0, "nova"])
    assert out.loc[1, "nova"] == "42"  # coluna nova criada como TEXT


@pytest.mark.pg
def test_sync_to_postgres_le_do_duckdb(pg_engine, pg_schema, tmp_path, monkeypatch):
    monkeypatch.setenv("DUCKDB_PATH", str(tmp_path / "silver.duckdb"))
    from govhub.ingestion.storage import silver

    lote = silver.write(pd.DataFrame({"ID": [1, 2, 3], "Nome UF": ["DF", "GO", "SP"]}), "ibge")
    n = silver_sync.sync_to_postgres(lote, "ibge", schema=pg_schema, engine=pg_engine)
    assert n == 3
    out = _rows(pg_engine, pg_schema, "ibge")
    assert out["nome_uf"].tolist() == ["DF", "GO", "SP"]


def test_nome_invalido_e_rejeitado():
    with pytest.raises(ValueError):
        silver_sync.sync_dataframe(pd.DataFrame({"id": [1]}), 'x"; drop table y; --', "lote",
                                   engine=object())
