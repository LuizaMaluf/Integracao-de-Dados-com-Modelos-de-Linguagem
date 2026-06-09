from typing import Any

from pydantic import BaseModel, computed_field


class PipelineConfig(BaseModel):
    tenant: str
    source: str
    schedule: str = "@daily"
    destination: str = "minio"
    filters: dict[str, Any] = {}
    retries: int = 1
    retry_delay_minutes: int = 5

    @computed_field
    @property
    def dag_id(self) -> str:
        return f"{self.tenant}__{self.source}"
