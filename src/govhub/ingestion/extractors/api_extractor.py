"""
Extracts data from paginated REST APIs (governmental and public).
Config keys: url, auth_strategy, auth_header, auth_env_var,
             pagination_strategy, page_param, page_size, page_size_param,
             params, records_path, has_more_field.
"""
import os
from typing import Any

import httpx
import pandas as pd

from .base import BaseExtractor


class ApiExtractor(BaseExtractor):
    """Fetches all pages from a REST API and returns a flat DataFrame."""

    def extract(self) -> pd.DataFrame:
        headers = self._build_headers()
        records: list[dict] = []
        page = 1

        with httpx.Client(timeout=30) as client:
            while True:
                params = dict(self.config.get("params", {}))
                strategy = self.config.get("pagination_strategy", "none")

                if strategy == "page_number":
                    params[self.config["page_param"]] = page
                    params[self.config.get("page_size_param", "size")] = self.config.get("page_size", 100)

                response = client.get(self.config["url"], headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                page_records = self._extract_records(data)
                records.extend(page_records)

                if not self._has_more(data, strategy):
                    break
                page += 1

        return pd.DataFrame(records)

    def _build_headers(self) -> dict:
        strategy = self.config.get("auth_strategy", "none")
        if strategy == "bearer":
            token = os.environ[self.config["auth_env_var"]]
            return {"Authorization": f"Bearer {token}"}
        if strategy == "api_key_header":
            token = os.environ[self.config["auth_env_var"]]
            return {self.config["auth_header"]: token}
        return {}

    def _extract_records(self, data: Any) -> list[dict]:
        path = self.config.get("records_path")
        if path:
            for key in path.split("."):
                data = data[key]
        if isinstance(data, list):
            return data
        return [data]

    def _has_more(self, data: Any, strategy: str) -> bool:
        if strategy == "none":
            return False
        field = self.config.get("has_more_field")
        if field and not data.get(field):
            return False
        return True
