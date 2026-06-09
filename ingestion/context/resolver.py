"""
ContextResolver — decides which dbt models to run based on confirmed
integration discoveries stored in the context schema.

Design decisions:
- Receives a ContextStore (or any object with .get_discoveries()) at
  construction time; never instantiates its own DB connection.
- get_select returns "models/" when at least one discovery meets the
  confidence threshold, falling back to "models/bronze/" otherwise.
  This maps directly to the --select argument passed to DbtTaskGroup.
- get_select_all is a convenience wrapper that resolves every package
  in a single call and returns a {package: select} mapping, which
  callers can zip straight into the DAG factory.
- Default min_confidence=0.7 mirrors the threshold used by
  ContextStore.get_discoveries so callers that don't override it get
  consistent behaviour without repeating the magic number.
"""
from __future__ import annotations

_BRONZE_ONLY = "models/bronze/"
_ALL_MODELS = "models/"


class ContextResolver:
    """Maps dbt package names to the correct --select path.

    Parameters
    ----------
    store:
        Any object that exposes ``get_discoveries(table_name, min_confidence)``
        and returns a list of discovery dicts.  In production this will be a
        ``ContextStore`` instance; in tests a ``MagicMock`` is sufficient.
    """

    def __init__(self, store) -> None:
        self._store = store

    def get_select(self, package_name: str, min_confidence: float = 0.7) -> str:
        """Return the dbt --select path for *package_name*.

        Parameters
        ----------
        package_name:
            The dbt package identifier, used as the ``table_name`` filter
            when querying integration discoveries.
        min_confidence:
            Minimum confidence threshold forwarded to ``store.get_discoveries``.
            Defaults to 0.7.

        Returns
        -------
        str
            ``"models/"`` when at least one discovery exists above the
            threshold; ``"models/bronze/"`` otherwise.
        """
        discoveries = self._store.get_discoveries(
            package_name, min_confidence=min_confidence
        )
        if discoveries:
            return _ALL_MODELS
        return _BRONZE_ONLY

    def get_select_all(
        self, packages: list[str], min_confidence: float = 0.7
    ) -> dict[str, str]:
        """Resolve --select for every package in *packages*.

        Parameters
        ----------
        packages:
            Ordered list of dbt package names to resolve.
        min_confidence:
            Forwarded unchanged to each ``get_select`` call.

        Returns
        -------
        dict[str, str]
            Mapping of ``{package_name: select_path}`` preserving the order
            of *packages*.
        """
        return {
            pkg: self.get_select(pkg, min_confidence=min_confidence)
            for pkg in packages
        }
