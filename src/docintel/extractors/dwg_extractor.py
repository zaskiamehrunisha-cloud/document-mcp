"""
DWG extractor for DOCINTEL.
Converts DWG to DXF using ODA File Converter, then extracts with ezdxf.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from docintel.common.exceptions import ExtractionError
from docintel.common.logging import get_logger
from docintel.common.constants import SOURCE_LAYER_NATIVE
from docintel.extractors.dxf_extractor import DXFExtractor

logger = get_logger(__name__)


class DWGExtractor:
    """
    Extracts text and metadata from DWG files.
    Uses ODA File Converter to convert DWG → DXF, then ezdxf for extraction.
    """
    
    def __init__(
        self,
        oda_converter_path: Optional[str] = None,
        output_version: str = "R2018",
    ):
        """
        Initialize the DWG extractor.
        
        Args:
            oda_converter_path: Path to ODA File Converter executable
            output_version: DXF version to convert to (e.g., "R2018")
        """
        self.oda_converter_path = oda_converter_path or self._find_oda_converter()
        self.output_version = output_version
        self.dxf_extractor = DXFExtractor()
    
    def _find_oda_converter(self) -> str:
        """
        Find the ODA File Converter executable.
        
        Returns:
            Path to the executable
            
        Raises:
            ExtractionError: If ODA File Converter is not found
        """
        # Common installation paths
        possible_paths = [
            # Windows
            r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
            r"C:\Program Files (x86)\ODA\ODAFileConverter\ODAFileConverter.exe",
            # Linux
            "/usr/bin/ODAFileConverter",
            "/usr/local/bin/ODAFileConverter",
            # macOS
            "/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found ODA File Converter at {path}")
                return path
        
        # Try to find in PATH
        try:
            result = subprocess.run(
                ["which", "ODAFileConverter"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                path = result.stdout.strip()
                logger.info(f"Found ODA File Converter in PATH: {path}")
                return path
        except Exception:
            pass
        
        error_msg = (
            "ODA File Converter not found. Please install it from "
            "https://www.opendesign.com/guestfiles/oda_file_converter "
            "and ensure it's in PATH or configure the path in settings."
        )
        logger.error(error_msg)
        raise ExtractionError(error_msg)
    
    def extract(self, file_path: str) -> dict:
        """
        Extract text and metadata from a DWG file.
        
        Args:
            file_path: Path to the DWG file
            
        Returns:
            Dictionary with 'text', 'metadata', and 'source_layer'
        """
        try:
            # Create temporary directory for conversion
            with tempfile.TemporaryDirectory() as tmpdir:
                # Convert DWG to DXF
                dxf_path = self._convert_to_dxf(file_path, tmpdir)
                
                # Extract from DXF
                result = self.dxf_extractor.extract(dxf_path)
                
                # Add DWG-specific metadata
                result["metadata"]["source_format"] = "DWG"
                result["metadata"]["source_file"] = file_path
                
                logger.info(
                    "DWG extraction complete",
                    extra={
                        "file": file_path,
                        "chars": len(result["text"]),
                    },
                )
                
                return result
                
        except ExtractionError:
            raise
        except Exception as e:
            error_msg = f"Failed to extract DWG: {str(e)}"
            logger.error(error_msg, extra={"file": file_path}, exc_info=True)
            raise ExtractionError(error_msg) from e
    
    def _convert_to_dxf(self, dwg_path: str, output_dir: str) -> str:
        """
        Convert DWG to DXF using ODA File Converter.
        
        Args:
            dwg_path: Path to the DWG file
            output_dir: Directory to write the DXF file
            
        Returns:
            Path to the converted DXF file
        """
        try:
            # ODA File Converter command line arguments:
            # ODAFileConverter <input_folder> <output_folder> <version> <recurse> <audit> <filter> <output_type>
            
            input_dir = os.path.dirname(os.path.abspath(dwg_path))
            input_file = os.path.basename(dwg_path)
            
            # Build command
            cmd = [
                self.oda_converter_path,
                input_dir,  # Input folder
                output_dir,  # Output folder
                self.output_version,  # Output version
                "0",  # Don't recurse subfolders
                "0",  # Don't audit
                "*.DWG",  # Filter
                "DXF",  # Output type
                "0",  # Don't export to object enabler
            ]
            
            logger.info(
                "Converting DWG to DXF",
                extra={"dwg": dwg_path, "output_dir": output_dir},
            )
            
            # Run conversion
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            
            if result.returncode != 0:
                error_msg = f"ODA conversion failed: {result.stderr}"
                logger.error(error_msg)
                raise ExtractionError(error_msg)
            
            # Find the output DXF file
            dxf_filename = input_file.rsplit(".", 1)[0] + ".dxf"
            dxf_path = os.path.join(output_dir, dxf_filename)
            
            if not os.path.exists(dxf_path):
                # Try case-insensitive search
                for file in os.listdir(output_dir):
                    if file.lower().endswith(".dxf"):
                        dxf_path = os.path.join(output_dir, file)
                        break
            
            if not os.path.exists(dxf_path):
                error_msg = f"DXF output not found after conversion: {dxf_path}"
                logger.error(error_msg)
                raise ExtractionError(error_msg)
            
            logger.info(f"DWG converted to DXF: {dxf_path}")
            return dxf_path
            
        except subprocess.TimeoutExpired:
            error_msg = "DWG conversion timed out after 5 minutes"
            logger.error(error_msg)
            raise ExtractionError(error_msg)
        except ExtractionError:
            raise
        except Exception as e:
            error_msg = f"DWG to DXF conversion failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ExtractionError(error_msg) from e
    
    def extract_page(self, file_path: str, page_number: int) -> dict:
        """
        DWG files don't have pages, but we support this for consistency.
        
        Args:
            file_path: Path to the DWG file
            page_number: Ignored for DWG
            
        Returns:
            Dictionary with 'text' and 'metadata'
        """
        return self.extract(file_path)
    
    def is_available(self) -> bool:
        """
        Check if ODA File Converter is available.
        
        Returns:
            True if available, False otherwise
        """
        try:
            return os.path.exists(self.oda_converter_path)
        except Exception:
            return False


# Global DWG extractor instance
_dwg_extractor: Optional[DWGExtractor] = None


def get_dwg_extractor() -> DWGExtractor:
    """Get the global DWG extractor instance."""
    global _dwg_extractor
    if _dwg_extractor is None:
        _dwg_extractor = DWGExtractor()
    return _dwg_extractor