"""
Downloads a PDF from a URL or reads it from a local path.
Returns the raw binary — parsing is delegated to parsers/.
Config keys: source_url, file_path.
"""
from pathlib import Path

import httpx

from .base import BaseExtractor


class PdfExtractor(BaseExtractor):
    """Downloads or reads a PDF binary and returns its bytes."""

    def extract(self) -> bytes:
        ...

    def _download(self, url: str) -> bytes:
        ...