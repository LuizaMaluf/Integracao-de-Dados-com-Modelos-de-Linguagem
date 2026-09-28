"""Fluxo completo A → B → C com dados no formato da API do IBGE.

Precisa de PostgreSQL (POSTGRES_*), do executável ``dbt`` e de ``dbt/dbt_packages``
instalado (``make dbt-deps``); sem isso o teste é pulado.
"""
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[2]

ESTADOS = pd.DataFrame({
    "id": [53, 52, 35, 31],
    "sigla": ["DF", "GO", "SP", "MG"],
    "nome": ["Distrito Federal", "Goiás", "São Paulo", "Minas Gerais"],
    "regiao": [{"id": 5, "sigla": "CO"}, {"id": 5, "sigla": "CO"},
               {"id": 3, "sigla": "SE"}, {"id": 3, "sigla": "SE"}],
})
MUNICIPIOS = pd.DataFrame({
    "id": [5300108, 5208707, 5201405, 3550308, 3509502, 3106200],
    "nome": ["Brasília", "Goiânia", "Aparecida de Goiânia", "São Paulo", "Campinas",
             "Belo Horizonte"],
    "microrregiao": [{"mesorregiao": {"UF": {"id": uf}}} for uf in (53, 52, 52, 35, 35, 31)],
})


@pytest.fixture
def e2e_env(pg_engine, tmp_path, monkeypatch):
    if shutil.which("dbt") is None:
        pytest.skip("dbt não instalado")
    if not (ROOT / "dbt" / "dbt_packages").exists():
        pytest.skip("rode `make dbt-deps` antes")

    dbt_dir = tmp_path / "dbt"
    shutil.copytree(ROOT / "dbt", dbt_dir, ignore=shutil.ignore_patterns("target", "logs"))
    configs = tmp_path / "configs"
    configs.mkdir()
    for name in ("ibge_estados.yaml", "ibge_municipios.yaml"):
        shutil.copy(ROOT / "airflow" / "configs" / name, configs / name)
    monkeypatch.setenv("DUCKDB_PATH", str(tmp_path / "silver.duckdb"))

    def drop_tables():
        with pg_engine.begin() as conn:
            for schema in ("silver", "bronze"):
                for table in ("ibge_estados", "ibge_municipios"):
                    conn.execute(text(f'DROP TABLE IF EXISTS "{schema}"."{table}"'))

    drop_tables()
    yield configs, dbt_dir
    drop_tables()


@pytest.mark.pg
@pytest.mark.e2e
def test_e2e_ibge(e2e_env, tmp_path):
    from govhub.ingestion.storage import silver
    from govhub.sync.e2e import E2EConfig, run_e2e

    configs, dbt_dir = e2e_env
    silver.write(ESTADOS, "ibge_estados")
    silver.write(MUNICIPIOS, "ibge_municipios")

    out = tmp_path / "resultado.json"
    result = run_e2e(E2EConfig(
        sources=("ibge_municipios", "ibge_estados"),
        configs_dir=configs, dbt_dir=dbt_dir, use_llm=False, output=out,
    ))

    e2e = result["e2e"]
    assert e2e["rows_synced"] == {"ibge_municipios": 6, "ibge_estados": 4}
    assert e2e["rows_loaded"] == {"ibge_municipios": 6, "ibge_estados": 4}
    assert e2e["read_schema"] == "bronze"
    assert {"B_generate", "B_dbt_run", "integration"} <= set(e2e["timings_s"])
    assert (dbt_dir / "models" / "bronze" / "_generated" / "ibge_municipios.sql").exists()
    assert result["best_match"]["table_a"] == "bronze.ibge_municipios"
    assert json.loads(out.read_text())["e2e"]["tables"] == ["ibge_municipios", "ibge_estados"]
