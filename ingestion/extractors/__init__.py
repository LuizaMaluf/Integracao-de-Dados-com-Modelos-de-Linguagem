from .api_extractor import ApiExtractor
from .base import BaseExtractor


def get_extractor(config: dict) -> BaseExtractor:
    tipo = config.get("type")
    if tipo == "api_series":
        return ApiExtractor(config)
    raise ValueError(f"Extractor não suportado: '{tipo}'. Disponíveis: ['api_series']")
