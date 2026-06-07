import pandas as pd
from pathlib import Path
from .base import BaseLoader, TableMetadata
from src.config.settings import settings


class CsvLoader(BaseLoader):
    def load(
        self,
        source: str,
        table_name: str | None = None,
        sample_size: int | None = None,
        encoding: str = "utf-8",
        sep: str = ";",
        descriptions: dict[str, str] | None = None,
        **kwargs,
    ) -> tuple[pd.DataFrame, TableMetadata]:
        path = Path(source)
        n = sample_size or settings.sample_size

        df_full = pd.read_csv(path, encoding=encoding, sep=sep, **kwargs)
        sample = df_full.sample(min(n, len(df_full)), random_state=42)

        metadata = TableMetadata(
            name=table_name or path.stem,
            columns=df_full.columns.tolist(),
            dtypes={col: str(dtype) for col, dtype in df_full.dtypes.items()},
            row_count=len(df_full),
            descriptions=descriptions or {},
            sample=sample,
        )
        return df_full, metadata
