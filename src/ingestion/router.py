"""File format router for document ingestion."""
import logging
from pathlib import Path
from typing import Optional

from src.common.constants import SUPPORTED_EXTENSIONS
from src.common.exceptions import IngestionError

logger = logging.getLogger(__name__)


class FormatRouter:
    """
    Routes files to appropriate extractors based on file extension.
    """
    
    def __init__(self):
        """Initialize format router."""
        self.routes = {
            ".pdf": "pdf",
            ".dwg": "cad",
            ".dxf": "cad",
            ".docx": "office",
            ".xlsx": "office",
            ".pptx": "office",
            ".png": "image",
            ".jpg": "image",
            ".jpeg": "image",
            ".tiff": "image",
            ".tif": "image",
        }
    
    def route(self, file_path: Path) -> str:
        """
        Determine the extractor type for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Extractor type string (pdf, cad, office, image)
            
        Raises:
            IngestionError: If file format is not supported
        """
        extension = file_path.suffix.lower()
        
        if extension not in SUPPORTED_EXTENSIONS:
            raise IngestionError(
                f"Unsupported file format: {extension}. "
                f"Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )
        
        extractor_type = self.routes.get(extension)
        logger.info(f"Routing {file_path.name} to {extractor_type} extractor")
        
        return extractor_type
    
    def is_supported(self, file_path: Path) -> bool:
        """
        Check if a file format is supported.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if format is supported
        """
        extension = file_path.suffix.lower()
        return extension in SUPPORTED_EXTENSIONS
    
    def get_supported_extensions(self) -> list[str]:
        """
        Get list of supported file extensions.
        
        Returns:
            Sorted list of supported extensions
        """
        return sorted(SUPPORTED_EXTENSIONS)


# Global router instance
format_router = FormatRouter()