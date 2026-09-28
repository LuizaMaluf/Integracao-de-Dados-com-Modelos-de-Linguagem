import json

import pandas as pd
import pytest

from govhub.ingestion.bridge import integration_bridge
from govhub.sync.silver_sync import sync_dataframe


def test_source_invalido(monkeypatch):
    with pytest.raises(ValueError):
        integration_bridge.run_integration("a", "b", use_llm=False, source="csv")


@pytest.mark.pg
def test_bridge_le_do_postgres(pg_engine, pg_schema, tmp_path, monkeypatch):
    sync_dataframe(pd.DataFrame({"cd_ug": [1, 2, 3]}), "a", "a_1",
                   schema=pg_schema, engine=pg_engine)
    sync_dataframe(pd.DataFrame({"ug": [1, 2, 4]}), "b", "b_1", schema=pg_schema, engine=pg_engine)
    monkeypatch.setattr(integration_bridge, "OUTPUT_DIR", tmp_path)

    out = integration_bridge.run_integration(
        f"{pg_schema}.a", f"{pg_schema}.b", use_llm=False, source="postgres"
    )
    result = json.loads(out.read_text())
    assert result["best_match"]["table_a"] == f"{pg_schema}.a"
    assert out.name == f"identificar_chave_{pg_schema}.a__{pg_schema}.b.json"
