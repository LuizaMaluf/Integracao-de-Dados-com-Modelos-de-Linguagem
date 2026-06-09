"""
Extracts data from REST APIs.
Supports auth strategies: none | bearer | api_key_header
Supports pagination strategies: none | page_number
Config keys used: url (generic) or base_url + serie (api_series),
                  auth_strategy, auth_header, auth_env_var,
                  pagination_strategy, page_param, page_size, page_size_param,
                  params, records_path, has_more_field
"""
import json
import os
from typing import Any

import httpx
from core.extractors.base import BaseExtractor


class ApiExtractor(BaseExtractor):
    """
    Fetches all pages from a REST API and returns a flat DataFrame.
    """

    def _build_url(self) -> str:
        serie = self.config.get("serie")
        if serie:
            base = f"{self.config['base_url']}/bcdata.sgs.{serie['codigo']}/dados"
            ultimos = self.config.get("ultimos")
            return f"{base}/ultimos/{ultimos}" if ultimos else base
        return self.config["url"]

    def extract_raw(self) -> str:
        """Fetch all pages and return the combined records as a JSON string."""
        headers = self._build_headers()
        records: list[dict] = []
        page = 1
        url = self._build_url()

        with httpx.Client(timeout=30) as client:
            while True:
                params = dict(self.config.get("params", {}))
                strategy = self.config.get("pagination_strategy", "none")

                if strategy == "page_number":
                    params[self.config["page_param"]] = page
                    params[self.config.get("page_size_param", "size")] = self.config.get("page_size", 100)

                response = client.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                page_records = self._extract_records(data)
                records.extend(page_records)

                if not self._has_more(data, strategy):
                    break
                page += 1

        return json.dumps(records)

    def _build_headers(self) -> dict:
        headers = {"Accept": "application/json"}
        strategy = self.config.get("auth_strategy", "none")
        if strategy == "bearer":
            token = os.environ[self.config["auth_env_var"]]
            headers["Authorization"] = f"Bearer {token}"
        elif strategy == "api_key_header":
            token = os.environ[self.config["auth_env_var"]]
            headers[self.config["auth_header"]] = token
        return headers

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
