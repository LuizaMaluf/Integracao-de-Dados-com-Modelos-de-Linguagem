def persist_discovery(result: dict, store) -> None:
    """Escreve o best_match de um resultado IntegrationAgent no ContextStore."""
    best = result.get("best_match")
    if not best:
        return

    candidates = result.get("candidate_keys", [])
    first = candidates[0] if candidates else {}

    store.upsert_discovery(
        table_a=best["table_a"],
        column_a=best["columns_a"][0],
        table_b=best["table_b"],
        column_b=best["columns_b"][0],
        confidence=best["confidence"],
        justification=best.get("justification"),
        evidence_for=first.get("evidence_for", []),
        evidence_against=first.get("evidence_against", []),
        required_transforms=first.get("required_transformations", []),
        discovery_method="semantic+content",
    )
