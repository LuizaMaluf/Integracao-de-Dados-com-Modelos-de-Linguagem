import json
import sys

import pandas as pd
import pytest

from govhub import cli
from govhub.sync.silver_sync import sync_dataframe


@pytest.mark.pg
def test_cli_integra_duas_tabelas_do_postgres(pg_engine, pg_schema, tmp_path, monkeypatch, capsys):
    a = pd.DataFrame({"cd_ug": [110001, 110002, 110003], "nome": ["A", "B", "C"]})
    b = pd.DataFrame({"ug_codigo": [110001, 110002, 110009], "valor": [10, 20, 30]})
    sync_dataframe(a, "ugs", "ugs_1", schema=pg_schema, engine=pg_engine)
    sync_dataframe(b, "pagamentos", "pagamentos_1", schema=pg_schema, engine=pg_engine)

    out = tmp_path / "resultado.json"
    monkeypatch.setattr(sys, "argv", [
        "govhub", "--table-a", f"pg://{pg_schema}.ugs", "--table-b", f"pg://{pg_schema}.pagamentos",
        "--no-llm", "--output", str(out),
    ])
    cli.main()

    result = json.loads(out.read_text())
    best = result["best_match"]
    assert best["columns_a"] == ["cd_ug"] and best["columns_b"] == ["ug_codigo"]
    colunas = {c for k in result["candidate_keys"]
               for c in k["table_a_columns"] + k["table_b_columns"]}
    assert not colunas & {"dt_ingest", "_silver_table"}
