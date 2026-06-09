import logging

log = logging.getLogger(__name__)


class _ProviderStub:
    def __init__(self, destination: str) -> None:
        self._destination = destination

    def write(self, data: dict, path: str) -> None:
        log.info(
            "[stub] write  destination=%s  path=%s  records=%d",
            self._destination,
            path,
            len(data.get("records", [])),
        )


def get_provider(destination: str) -> _ProviderStub:
    return _ProviderStub(destination)
