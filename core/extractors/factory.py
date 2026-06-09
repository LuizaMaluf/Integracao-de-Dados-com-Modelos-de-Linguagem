from core.extractors.api_extractor import ApiExtractor
from core.extractors.base import BaseExtractor
from core.extractors.csv_extractor import CsvExtractor
from core.extractors.dump_extractor import DumpExtractor
from core.extractors.pdf_extractor import PdfExtractor

_EXTRACTOR_REGISTRY: dict[str, type[BaseExtractor]] = {
    "api": ApiExtractor,
    "api_series": ApiExtractor,
    "csv_xlsx": CsvExtractor,
    "dump": DumpExtractor,
    "pdf": PdfExtractor,
    "pdf_structural": PdfExtractor,
    "pdf_semantic": PdfExtractor,
}


def get_extractor(cfg: dict) -> BaseExtractor:
    source_type = cfg.get("type")
    cls = _EXTRACTOR_REGISTRY.get(source_type)
    if cls is None:
        raise ValueError(f"Unknown extractor type: '{source_type}'. Available: {list(_EXTRACTOR_REGISTRY)}")
    return cls(cfg)
