from unittest.mock import MagicMock


def make_result(confidence=0.94):
    return {
        "best_match": {
            "table_a": "mir.empenhos",
            "columns_a": ["nr_empenho"],
            "table_b": "siafi.notas_empenho",
            "columns_b": ["num_empenho"],
            "confidence": confidence,
            "justification": "Mesmo grupo semântico empenho",
        },
        "candidate_keys": [{
            "table_a_columns": ["nr_empenho"],
            "table_b_columns": ["num_empenho"],
            "score": confidence,
            "evidence_for": ["domain_group_match"],
            "evidence_against": [],
            "required_transformations": [],
        }],
    }


def test_persist_discovery_calls_upsert():
    store = MagicMock()
    from bridge.context_writer import persist_discovery
    persist_discovery(make_result(), store)

    store.upsert_discovery.assert_called_once()
    kw = store.upsert_discovery.call_args[1]
    assert kw["table_a"] == "mir.empenhos"
    assert kw["column_a"] == "nr_empenho"
    assert kw["table_b"] == "siafi.notas_empenho"
    assert kw["column_b"] == "num_empenho"
    assert kw["confidence"] == 0.94
    assert "Mesmo grupo" in kw["justification"]
    assert "domain_group_match" in kw["evidence_for"]


def test_persist_discovery_no_best_match_does_nothing():
    store = MagicMock()
    from bridge.context_writer import persist_discovery
    persist_discovery({"best_match": None, "candidate_keys": []}, store)
    store.upsert_discovery.assert_not_called()


def test_persist_discovery_multi_column_uses_first():
    store = MagicMock()
    result = make_result()
    result["best_match"]["columns_a"] = ["ano", "nr_empenho"]
    result["best_match"]["columns_b"] = ["exercicio", "num_empenho"]
    from bridge.context_writer import persist_discovery
    persist_discovery(result, store)
    kw = store.upsert_discovery.call_args[1]
    assert kw["column_a"] == "ano"
    assert kw["column_b"] == "exercicio"
