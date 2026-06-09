import logging
from typing import Any

log = logging.getLogger(__name__)


class _ExtractorStub:
    def __init__(self, source: str) -> None:
        self._source = source

    def run(self, filters: dict[str, Any] | None = None) -> dict:
        log.info("[stub] extract  source=%s  filters=%s", self._source, filters)
        return {"records": [], "source": self._source, "filters": filters}


def get_extractor(source: str) -> _ExtractorStub:
    return _ExtractorStub(source)
