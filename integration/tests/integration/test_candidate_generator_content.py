"""
Integration test: CandidateGenerator promotes pairs via Content Evidence Layer
when semantic similarity is below the threshold but content_score is high.
"""
import pandas as pd
import pytest

from src.agent.candidate_generator import CandidateGenerator
from src.loaders.base import TableMetadata


def _meta(df: pd.DataFrame, name: str) -> TableMetadata:
    return TableMetadata(
        name=name,
        columns=list(df.columns),
        dtypes={col: str(dtype) for col, dtype in df.dtypes.items()},
        row_count=len(df),
        sample=df.head(5).to_dict(orient="records"),
    )


def test_content_path_promotes_renamed_column():
    """A column with a completely unrelated name (semantic_score < 0.30) but 100%
    value overlap must be found via the Content Evidence Layer.

    'chave_x' vs 'id_y' has semantic_score ≈ 0.18, so it goes to the content path.
    """
    shared_values = [f"REG{i:05d}" for i in range(50)]

    df_a = pd.DataFrame({"chave_x": shared_values})
    df_b = pd.DataFrame({"id_y": shared_values})   # semantic_score ≈ 0.18

    meta_a = _meta(df_a, "table_alpha")
    meta_b = _meta(df_b, "table_beta")

    gen = CandidateGenerator(df_a, meta_a, df_b, meta_b, semantic_threshold=0.3)
    candidates = gen.generate()

    content_promoted = [c for c in candidates if c.content_score is not None]
    assert len(content_promoted) >= 1, "Expected at least one content-promoted candidate"

    best = content_promoted[0]
    assert best.columns_a == ["chave_x"]
    assert best.columns_b == ["id_y"]
    assert best.content_score >= 0.50


def test_semantic_path_still_works():
    """Pairs with high name similarity must still come through the semantic path."""
    shared_values = [f"NE{i:06d}" for i in range(50)]

    df_a = pd.DataFrame({"nr_empenho": shared_values})
    df_b = pd.DataFrame({"num_empenho": shared_values})

    meta_a = _meta(df_a, "empenhos_a")
    meta_b = _meta(df_b, "empenhos_b")

    gen = CandidateGenerator(df_a, meta_a, df_b, meta_b)
    candidates = gen.generate()

    semantic = [c for c in candidates if c.content_score is None]
    assert len(semantic) >= 1

    best = semantic[0]
    assert best.semantic_score >= 0.75


def test_no_false_promotion_with_zero_overlap():
    """Pairs with zero value overlap and no substring relation must not be promoted."""
    df_a = pd.DataFrame({"col_x": [f"A{i}" for i in range(50)]})
    df_b = pd.DataFrame({"col_y": [f"Z{i}" for i in range(50)]})

    meta_a = _meta(df_a, "table_a")
    meta_b = _meta(df_b, "table_b")

    gen = CandidateGenerator(df_a, meta_a, df_b, meta_b, semantic_threshold=0.9)
    candidates = gen.generate()

    # With threshold=0.9 everything goes to content path; overlap is 0 → no promotion
    content_promoted = [c for c in candidates if c.content_score is not None]
    assert len(content_promoted) == 0
