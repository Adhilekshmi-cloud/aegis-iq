"""Document ingestion module for Aegis Knowledge System."""

from app.ingestion.docx_extractor import DOCXExtractor
from app.ingestion.html_extractor import HTMLExtractor
from app.ingestion.json_extractor import JSONExtractor
from app.ingestion.ocr_extractor import OCRExtractor
from app.ingestion.pdf_extractor import PDFExtractor
from app.ingestion.pipeline import (
    DocumentIngestionReport,
    IngestionPipeline,
    IngestionPipelineReport,
    build_default_registry,
    map_extension_to_doc_type,
)
from app.ingestion.png_extractor import PNGExtractor
from app.ingestion.pptx_extractor import PPTXExtractor
from app.ingestion.registry import (
    ExtractionResult,
    ExtractorProtocol,
    ExtractorRegistry,
    default_extractor_registry,
)
from app.ingestion.xlsx_extractor import XLSXExtractor

__all__ = [
    "ExtractionResult",
    "ExtractorProtocol",
    "ExtractorRegistry",
    "default_extractor_registry",
    "PDFExtractor",
    "OCRExtractor",
    "HTMLExtractor",
    "DOCXExtractor",
    "XLSXExtractor",
    "PPTXExtractor",
    "JSONExtractor",
    "PNGExtractor",
    "DocumentIngestionReport",
    "IngestionPipelineReport",
    "IngestionPipeline",
    "build_default_registry",
    "map_extension_to_doc_type",
]
