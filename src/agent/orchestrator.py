"""
Main orchestrator: ties loaders, analyzers, candidate generator, and LLM reasoner.
"""
import json
from pathlib import Path

import pandas as pd

from src.loaders.base import TableMetadata
from src.agent.candidate_generator import CandidateGenerator
from src.agent.llm_reasoner import reason_with_llm
from src.config.settings import settings


class IntegrationAgent:
    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm

    def run(
        self,
        df_a: pd.DataFrame,
        meta_a: TableMetadata,
        df_b: pd.DataFrame,
        meta_b: TableMetadata,
    ) -> dict:
        generator = CandidateGenerator(
            df_a, meta_a, df_b, meta_b,
            semantic_threshold=0.3,
            max_candidates=settings.max_candidate_keys,
        )
        candidates = generator.generate()

        if not candidates:
            return {
                "summary": "No candidate keys found above threshold.",
                "candidate_keys": [],
                "best_match": None,
            }

        if self.use_llm:
            result = reason_with_llm(meta_a, meta_b, candidates)
        else:
            best = candidates[0]
            result = {
                "summary": f"Best candidate: {best.columns_a} ↔ {best.columns_b} (score={best.score})",
                "candidate_keys": [
                    {
                        "table_a_columns": c.columns_a,
                        "table_b_columns": c.columns_b,
                        "score": c.score,
                        "match_rate": c.match_rate,
                        "cardinality": c.cardinality,
                        "evidence_for": c.evidence_for,
                        "evidence_against": c.evidence_against,
                        "required_transformations": c.required_transformations,
                        "decision": "accepted" if c == best else "candidate",
                    }
                    for c in candidates
                ],
                "best_match": {
                    "table_a": meta_a.name,
                    "columns_a": best.columns_a,
                    "table_b": meta_b.name,
                    "columns_b": best.columns_b,
                    "confidence": best.score,
                    "justification": " | ".join(best.evidence_for),
                },
            }

        return result

    def save(self, result: dict, output_path: str | None = None) -> Path:
        out_dir = settings.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        path = Path(output_path) if output_path else out_dir / "integration_result.json"
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        return path
