from pathlib import Path

import pandas as pd

from govhub.integration.config.settings import settings

from .base import BaseLoader, TableMetadata


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

        metadata = TableMetadata.from_dataframe(
            df_full, table_name or path.stem, sample=sample, descriptions=descriptions
        )
        return df_full, metadata
