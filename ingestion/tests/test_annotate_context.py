import pytest
from unittest.mock import MagicMock, patch, call


def test_annotates_known_columns():
    """Colunas com domain_group conhecido são anotadas com o grupo correto."""
    store = MagicMock()
    columns = ["nr_empenho", "cd_orgao", "valor_total"]

    with patch("context.annotate_context.find_domain_group") as mock_fdg:
        mock_fdg.side_effect = lambda col, store=None: {
            "nr_empenho": "empenho",
            "cd_orgao": "orgao",
        }.get(col)

        from context.annotate_context import annotate_table
        annotate_table("mir.empenhos", columns, store)

    # deve ter chamado upsert_column_annotation para cada coluna
    assert store.upsert_column_annotation.call_count == 3
    store.upsert_column_annotation.assert_any_call(
        "mir.empenhos", "nr_empenho", domain_group="empenho", semantic_tags=None
    )
    store.upsert_column_annotation.assert_any_call(
        "mir.empenhos", "cd_orgao", domain_group="orgao", semantic_tags=None
    )
    store.upsert_column_annotation.assert_any_call(
        "mir.empenhos", "valor_total", domain_group=None, semantic_tags=None
    )


def test_empty_columns_does_nothing():
    """Lista vazia de colunas não chama o store."""
    store = MagicMock()
    from context.annotate_context import annotate_table
    annotate_table("mir.empenhos", [], store)
    store.upsert_column_annotation.assert_not_called()


def test_passes_store_to_find_domain_group():
    """find_domain_group é chamada com o store para usar domain_contexts customizados."""
    store = MagicMock()
    columns = ["nr_empenho"]

    with patch("context.annotate_context.find_domain_group") as mock_fdg:
        mock_fdg.return_value = "empenho"
        from context.annotate_context import annotate_table
        annotate_table("mir.empenhos", columns, store)

        mock_fdg.assert_called_once_with("nr_empenho", store=store)


def test_annotate_from_dataframe():
    """annotate_from_df extrai colunas do DataFrame e chama annotate_table."""
    import pandas as pd
    store = MagicMock()
    df = pd.DataFrame({"nr_empenho": [1, 2], "cd_orgao": ["001", "002"]})

    with patch("context.annotate_context.annotate_table") as mock_at:
        from context.annotate_context import annotate_from_df
        annotate_from_df("mir.empenhos", df, store)
        mock_at.assert_called_once_with(
            "mir.empenhos", list(df.columns), store
        )
