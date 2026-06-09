from pydantic import BaseModel


class SourceConfig(BaseModel):
    name: str
    auth_type: str = "none"
    base_url: str
    rate_limit_rps: float = 10.0
