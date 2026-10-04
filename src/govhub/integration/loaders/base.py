from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class TableMetadata:
    name: str
    columns: list[str]
    dtypes: dict[str, str]
    row_count: int
    descriptions: dict[str, str] = field(default_factory=dict)
    sample: pd.DataFrame = field(default_factory=pd.DataFrame)

    @classmethod
    def from_dataframe(
        cls,
        df: pd.DataFrame,
        name: str,
        sample: pd.DataFrame | None = None,
        descriptions: dict[str, str] | None = None,
    ) -> "TableMetadata":
        """Metadata de um DataFrame; ``sample`` padrão são as 5 primeiras linhas."""
        return cls(
            name=name,
            columns=list(df.columns),
            dtypes={col: str(dtype) for col, dtype in df.dtypes.items()},
            row_count=len(df),
            descriptions=descriptions or {},
            sample=df.head(5) if sample is None else sample,
        )

    def column_info(self) -> list[dict]:
        return [
            {
                "name": col,
                "dtype": self.dtypes.get(col, "unknown"),
                "description": self.descriptions.get(col, ""),
                "sample_values": self.sample[col].dropna().head(5).tolist()
                if col in self.sample.columns
                else [],
            }
            for col in self.columns
        ]


class BaseLoader(ABC):
    @abstractmethod
    def load(self, source: str, **kwargs) -> tuple[pd.DataFrame, TableMetadata]:
        """Load data and return (dataframe, metadata)."""
        ...
