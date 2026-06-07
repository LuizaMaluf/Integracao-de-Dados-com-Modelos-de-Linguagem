from pydantic_settings import BaseSettings
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    # LLM
    anthropic_api_key: str = ""
    model_name: str = "claude-sonnet-4-6"

    # Thresholds
    min_match_rate: float = 0.5
    min_confidence: float = 0.6
    max_candidate_keys: int = 10

    # Data
    sample_size: int = 1000
    data_dir: Path = ROOT_DIR / "data"
    raw_dir: Path = ROOT_DIR / "data" / "raw"
    processed_dir: Path = ROOT_DIR / "data" / "processed"

    # Output
    output_dir: Path = ROOT_DIR / "output"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
