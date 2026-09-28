"""
Structural PDF parser: finds pages matching a title pattern and extracts tables.
Primary tool: pdfplumber. Fallback: camelot (lattice mode) when pdfplumber returns
empty or single-column results.
Config keys: page_selector.contains_text, tables_per_page.
"""
from io import BytesIO

import pandas as pd


class StructuralPdfParser:
    """Extracts tables from PDF pages whose text matches a configured title string."""

    def __init__(self, config: dict):
        self.contains_text: str = config["page_selector"]["contains_text"]
        self.tables_per_page: str | int = config.get("tables_per_page", "all")

    def parse(self, pdf_bytes: bytes) -> pd.DataFrame:
        """Return a merged DataFrame of all tables found on matching pages."""
        frames = self._extract_with_pdfplumber(pdf_bytes)
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)

    def _extract_with_pdfplumber(self, pdf_bytes: bytes) -> list[pd.DataFrame]:
        import pdfplumber

        frames: list[pd.DataFrame] = []
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                if self.contains_text.lower() not in text.lower():
                    continue
                tables = page.extract_tables()
                selected = self._select_tables(tables)
                for raw in selected:
                    if not raw:
                        continue
                    df = pd.DataFrame(raw[1:], columns=raw[0])
                    if df.shape[1] <= 1:
                        # Single-column output likely means layout wasn't detected — fall back
                        df = self._fallback_camelot(pdf_bytes, page.page_number)
                    if df is not None and not df.empty:
                        frames.append(df)
        return frames

    def _fallback_camelot(self, pdf_bytes: bytes, page_number: int) -> pd.DataFrame | None:
        import tempfile, os
        import camelot

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        try:
            tables = camelot.read_pdf(tmp_path, pages=str(page_number), flavor="lattice")
            if tables:
                return tables[0].df
        except Exception:
            pass
        finally:
            os.unlink(tmp_path)
        return None

    def _select_tables(self, tables: list) -> list:
        if self.tables_per_page == "all":
            return tables
        if self.tables_per_page == "first":
            return tables[:1]
        if self.tables_per_page == "last":
            return tables[-1:]
        return tables[: int(self.tables_per_page)]
