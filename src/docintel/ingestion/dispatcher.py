"""
Ingestion dispatcher for DOCINTEL.
Routes files to the appropriate extractor based on MIME type and extension.
Decides whether to use native extraction or OCR fallback.
"""

import mimetypes
from pathlib import Path
from typing import Optional

from docintel.common.constants import SUPPORTED_EXTENSIONS, SUPPORTED_MIME_TYPES
from docintel.common.exceptions import ExtractionError, UnsupportedFormatError
from docintel.common.logging import get_logger
from docintel.ocr.text_layer import TextLayerAnalyzer

logger = get_logger(__name__)


class IngestionDispatcher:
    """
    Dispatches files to the appropriate extractor.
    Determines extraction strategy (native vs OCR) based on file type.
    """
    
    def __init__(self):
        """Initialize the dispatcher."""
        self.text_analyzer = TextLayerAnalyzer()
        self._extractors = {}
    
    def _get_extractor(self, file_type: str):
        """
        Get the appropriate extractor for a file type.
        
        Args:
            file_type: File type string (e.g., "pdf", "dxf", "docx")
            
        Returns:
            Extractor instance
            
        Raises:
            UnsupportedFormatError: If the file type is not supported
        """
        if file_type in self._extractors:
            return self._extractors[file_type]
        
        extractor = None
        
        if file_type == "pdf":
            from docintel.extractors.pdf_extractor import get_pdf_extractor
            extractor = get_pdf_extractor()
        elif file_type == "dxf":
            from docintel.extractors.dxf_extractor import get_dxf_extractor
            extractor = get_dxf_extractor()
        elif file_type == "dwg":
            from docintel.extractors.dwg_extractor import get_dwg_extractor
            extractor = get_dwg_extractor()
        elif file_type == "docx":
            from docintel.extractors.docx_extractor import get_docx_extractor
            extractor = get_docx_extractor()
        elif file_type == "xlsx":
            from docintel.extractors.xlsx_extractor import get_xlsx_extractor
            extractor = get_xlsx_extractor()
        elif file_type == "pptx":
            from docintel.extractors.pptx_extractor import get_pptx_extractor
            extractor = get_pptx_extractor()
        
        if extractor is None:
            raise UnsupportedFormatError(
                file_type=file_type,
                supported_types=list(SUPPORTED_MIME_TYPES.values()),
            )
        
        self._extractors[file_type] = extractor
        return extractor
    
    def detect_file_type(self, file_path: str) -> str:
        """
        Detect the file type from path and MIME type.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File type string (e.g., "pdf", "docx")
            
        Raises:
            UnsupportedFormatError: If the file type is not supported
        """
        path = Path(file_path)
        extension = path.suffix.lower()
        
        # Check by extension first
        if extension in SUPPORTED_EXTENSIONS:
            return SUPPORTED_EXTENSIONS[extension]
        
        # Try MIME type detection
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and mime_type in SUPPORTED_MIME_TYPES:
            return SUPPORTED_MIME_TYPES[mime_type]
        
        # Try to read the file header
        try:
            with open(file_path, "rb") as f:
                header = f.read(8)
                
                # PDF signature
                if header.startswith(b"%PDF"):
                    return "pdf"
                
                # DXF signature (ASCII)
                if header.startswith(b"0\nSECTION\n"):
                    return "dxf"
                
                # ZIP-based formats (DOCX, XLSX, PPTX)
                if header.startswith(b"PK\x03\x04"):
                    # Need to check further
                    if extension == ".docx":
                        return "docx"
                    elif extension == ".xlsx":
                        return "xlsx"
                    elif extension == ".pptx":
                        return "pptx"
        except Exception as e:
            logger.warning(f"Could not read file header: {str(e)}")
        
        raise UnsupportedFormatError(
            file_type=extension or "unknown",
            supported_types=list(SUPPORTED_MIME_TYPES.values()),
        )
    
    def dispatch(
        self,
        file_path: str,
        force_ocr: bool = False,
    ) -> dict:
        """
        Dispatch a file to the appropriate extractor.
        
        Args:
            file_path: Path to the file
            force_ocr: If True, force OCR even if native text exists
            
        Returns:
            Dictionary with 'text', 'metadata', 'source_layer', and 'file_type'
            
        Raises:
            UnsupportedFormatError: If the file type is not supported
            ExtractionError: If extraction fails
        """
        try:
            # Detect file type
            file_type = self.detect_file_type(file_path)
            logger.info(
                "Dispatching file",
                extra={"file": file_path, "type": file_type},
            )
            
            # Get the appropriate extractor
            extractor = self._get_extractor(file_type)
            
            # For PDFs, decide between native extraction and OCR
            if file_type == "pdf" and not force_ocr:
                use_native = self.text_analyzer.has_reliable_text_layer(file_path)
                
                if use_native:
                    logger.info("Using native text extraction for PDF")
                    result = extractor.extract(file_path)
                else:
                    logger.info("Using OCR fallback for PDF")
                    # Use OCR fallback
                    from docintel.ocr.paddle_engine import get_paddle_ocr
                    from docintel.ocr.tesseract_engine import get_tesseract
                    from docintel.config.settings import settings
                    
                    if settings.ocr_engine == "paddle":
                        ocr_engine = get_paddle_ocr()
                    else:
                        ocr_engine = get_tesseract()
                    
                    text = ocr_engine.ocr_pdf(file_path)
                    result = {
                        "text": text,
                        "metadata": extractor.extract(file_path)["metadata"],
                        "source_layer": "ocr",
                    }
            else:
                # Use native extraction
                result = extractor.extract(file_path)
            
            # Add file type to result
            result["file_type"] = file_type
            
            logger.info(
                "Dispatch complete",
                extra={
                    "file": file_path,
                    "type": file_type,
                    "source_layer": result.get("source_layer"),
                    "text_length": len(result.get("text", "")),
                },
            )
            
            return result
            
        except (UnsupportedFormatError, ExtractionError):
            raise
        except Exception as e:
            error_msg = f"Dispatch failed: {str(e)}"
            logger.error(error_msg, extra={"file": file_path}, exc_info=True)
            raise ExtractionError(error_msg) from e
    
    def is_supported(self, file_path: str) -> bool:
        """
        Check if a file type is supported.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if the file type is supported
        """
        try:
            self.detect_file_type(file_path)
            return True
        except UnsupportedFormatError:
            return False
        except Exception:
            return False


# Global dispatcher instance
_dispatcher: Optional[IngestionDispatcher] = None


def get_dispatcher() -> IngestionDispatcher:
    """Get the global dispatcher instance."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = IngestionDispatcher()
    return _dispatcher