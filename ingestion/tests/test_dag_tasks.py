import pytest
from unittest.mock import MagicMock, patch, call
import pandas as pd


def test_annotate_context_task_called_after_stage_silver():
    """annotate_from_df é chamado com table_name e df corretos."""
    store = MagicMock()
    df = pd.DataFrame({"nr_empenho": [1], "cd_orgao": ["001"]})

    with patch("context.annotate_context.find_domain_group") as mock_fdg:
        mock_fdg.return_value = None
        from context.annotate_context import annotate_from_df
        annotate_from_df("mir.empenhos", df, store)

    assert store.upsert_column_annotation.call_count == 2


def test_profile_table_writes_to_store():
    """profile_table escreve row_count e quality_ok no store."""
    store = MagicMock()
    df = pd.DataFrame({"nr_empenho": [1, 2, 3], "cd_orgao": ["001", "002", None]})

    from context.profile_context import profile_table
    profile_table("mir.empenhos", df, store)

    store.upsert_table_profile.assert_called_once()
    call_kwargs = store.upsert_table_profile.call_args[1]
    assert call_kwargs["table_name"] == "mir.empenhos"
    assert call_kwargs["row_count"] == 3
    assert "quality_ok" in call_kwargs


def test_profile_table_empty_df():
    """DataFrame vazio: row_count=0, quality_ok=True."""
    store = MagicMock()
    df = pd.DataFrame({"nr_empenho": []})
    from context.profile_context import profile_table
    profile_table("mir.empenhos", df, store)
    call_kwargs = store.upsert_table_profile.call_args[1]
    assert call_kwargs["row_count"] == 0
