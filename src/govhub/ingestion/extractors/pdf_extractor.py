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
        if "source_url" in self.config:
            return self._download(self.config["source_url"])
        return Path(self.config["file_path"]).read_bytes()

    def _download(self, url: str) -> bytes:
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.content
