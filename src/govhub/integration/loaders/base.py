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
