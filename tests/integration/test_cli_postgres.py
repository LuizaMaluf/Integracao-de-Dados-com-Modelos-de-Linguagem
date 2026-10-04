import json
import sys

import pandas as pd
import pytest

from govhub import cli


@pytest.mark.pg
def test_cli_integra_duas_tabelas_do_postgres(pg_engine, pg_schema, tmp_path, monkeypatch, capsys):
    linhagem = {"dt_ingest": pd.Timestamp("2026-09-28")}
    a = pd.DataFrame({"cd_ug": [110001, 110002, 110003], "nome": ["A", "B", "C"],
                      **linhagem, "_silver_table": "ugs_1"})
    b = pd.DataFrame({"ug_codigo": [110001, 110002, 110009], "valor": [10, 20, 30],
                      **linhagem, "_silver_table": "pagamentos_1"})
    a.to_sql("ugs", pg_engine, schema=pg_schema, index=False)
    b.to_sql("pagamentos", pg_engine, schema=pg_schema, index=False)

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
