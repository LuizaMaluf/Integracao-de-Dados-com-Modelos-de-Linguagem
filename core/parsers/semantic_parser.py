"""
Semantic PDF parser: classifies page elements with unstructured, then asks
the Claude API to convert relevant narrative text into a structured table.
Config keys: pages, semantic_prompt.
"""
import json
import logging
import os
from io import BytesIO

import pandas as pd

logger = logging.getLogger(__name__)


class SemanticPdfParser:
    """Uses layout analysis + LLM to extract structured tables from narrative PDF text."""

    def __init__(self, config: dict):
        self.pages = config.get("pages", "all")
        self.prompt: str = config["semantic_prompt"]
        self.model: str = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    def parse(self, pdf_bytes: bytes) -> pd.DataFrame:
        """Return a DataFrame built from LLM-extracted records across all selected pages."""
        text_blocks = self._extract_text_blocks(pdf_bytes)
        if not text_blocks:
            logger.warning("SemanticPdfParser: no NarrativeText blocks found in PDF.")
            return pd.DataFrame()

        records = self._call_llm(text_blocks)
        if records is None:
            raise ValueError("SemanticPdfParser: LLM returned an invalid response. Task failed.")
        return pd.DataFrame(records)

    def _extract_text_blocks(self, pdf_bytes: bytes) -> list[str]:
        """Use unstructured to classify elements and return NarrativeText content."""
        from unstructured.partition.pdf import partition_pdf

        elements = partition_pdf(file=BytesIO(pdf_bytes))
        page_filter = self._build_page_filter(elements)

        blocks: list[str] = []
        for el in elements:
            if page_filter and el.metadata.page_number not in page_filter:
                continue
            if el.category in ("NarrativeText", "Table"):
                blocks.append(str(el))
        return blocks

    def _build_page_filter(self, elements) -> set[int] | None:
        if self.pages == "all":
            return None
        if self.pages == "first":
            return {1}
        if self.pages == "last":
            max_page = max((el.metadata.page_number or 0) for el in elements)
            return {max_page}
        if isinstance(self.pages, list):
            return set(self.pages)
        return None

    def _call_llm(self, text_blocks: list[str]) -> list[dict] | None:
        import anthropic

        client = anthropic.Anthropic()
        combined_text = "\n\n".join(text_blocks)
        full_prompt = f"{self.prompt}\n\n---\n\n{combined_text}"

        message = client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": full_prompt}],
        )
        raw = message.content[0].text.strip()

        try:
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, IndexError):
            logger.error("SemanticPdfParser: could not parse LLM JSON response: %s", raw[:200])
        return None
