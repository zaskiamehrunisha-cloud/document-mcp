"""CAD extractor for DWG/DXF files using ODA File Converter and ezdxf."""
import io
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import PIL
from PIL import Image

from src.ocr.engine import ocr_engine
from src.ocr.confidence import ConfidenceGate
from src.common.exceptions import IngestionError, OCRError
from src.common.constants import OCR_FALLBACK_DPI

logger = logging.getLogger(__name__)


class CADExtractor:
    """
    CAD extractor for DWG/DXF files.
    Uses ODA File Converter to convert DWG to DXF, then ezdxf for parsing.
    Falls back to 150 DPI raster OCR if attribute extraction is incomplete.
    """
    
    def __init__(self):
        """Initialize CAD extractor."""
        self.confidence_gate = ConfidenceGate()
        self.oda_converter_path = self._find_oda_converter()
    
    def _find_oda_converter(self) -> Optional[str]:
        """
        Find ODA File Converter binary.
        
        Returns:
            Path to ODA File Converter or None if not found
        """
        # Common installation paths
        possible_paths = [
            "/usr/bin/ODAFileConverter",
            "/usr/local/bin/ODAFileConverter",
            "C:\\Program Files\\ODA\\ODAFileConverter\\ODAFileConverter.exe",
            "C:\\Program Files (x86)\\ODA\\ODAFileConverter\\ODAFileConverter.exe",
        ]
        
        for path in possible_paths:
            if Path(path).exists():
                logger.info(f"Found ODA File Converter at {path}")
                return path
        
        logger.warning("ODA File Converter not found. DWG files will use OCR-only extraction.")
        return None
    
    def extract(self, file_path: Path, page_count: Optional[int] = None) -> dict:
        """
        Extract text and metadata from CAD file.
        
        Args:
            file_path: Path to DWG or DXF file
            page_count: Optional known page count
            
        Returns:
            Dictionary with extracted text, metadata, and low-confidence regions
        """
        extension = file_path.suffix.lower()
        
        try:
            if extension == ".dwg":
                return self._extract_dwg(file_path)
            elif extension == ".dxf":
                return self._extract_dxf(file_path)
            else:
                raise IngestionError(f"Unsupported CAD format: {extension}")
        
        except Exception as e:
            logger.error(f"CAD extraction failed: {e}", exc_info=True)
            raise IngestionError(f"CAD extraction failed: {e}") from e
    
    def _extract_dwg(self, file_path: Path) -> dict:
        """
        Extract from DWG file (requires conversion to DXF).
        
        Args:
            file_path: Path to DWG file
            
        Returns:
            Extraction results
        """
        if not self.oda_converter_path:
            logger.warning("ODA File Converter not available, using OCR fallback")
            return self._extract_with_ocr(file_path)
        
        # Convert DWG to DXF using ODA File Converter
        with tempfile.TemporaryDirectory() as temp_dir:
            dxf_path = self._convert_dwg_to_dxf(file_path, Path(temp_dir))
            
            if dxf_path and dxf_path.exists():
                return self._extract_dxf(dxf_path)
            else:
                logger.warning("DWG to DXF conversion failed, using OCR fallback")
                return self._extract_with_ocr(file_path)
    
    def _convert_dwg_to_dxf(self, dwg_path: Path, output_dir: Path) -> Optional[Path]:
        """
        Convert DWG to DXF using ODA File Converter.
        
        Args:
            dwg_path: Path to DWG file
            output_dir: Output directory for DXF
            
        Returns:
            Path to converted DXF file or None if conversion failed
        """
        try:
            output_dxf = output_dir / f"{dwg_path.stem}.dxf"
            
            # ODA File Converter command line
            # Format: ODAFileConverter <input> <output> <version> <revision> <type> <output_format> <recursive> <audit> <password>
            cmd = [
                self.oda_converter_path,
                str(dwg_path.parent),
                str(output_dir),
                "ACAD2018",  # Output version
                "DWG",  # Input type
                "DXF",  # Output format
                "0",  # Not recursive
                "0",  # No audit
                "",  # No password
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully converted {dwg_path.name} to DXF")
                return output_dxf
            else:
                logger.error(f"ODA conversion failed: {result.stderr}")
                return None
        
        except subprocess.TimeoutExpired:
            logger.error("ODA File Converter timeout")
            return None
        except Exception as e:
            logger.error(f"DWG conversion failed: {e}")
            return None
    
    def _extract_dxf(self, dxf_path: Path) -> dict:
        """
        Extract text and metadata from DXF file using ezdxf.
        
        Args:
            dxf_path: Path to DXF file
            
        Returns:
            Extraction results
        """
        try:
            import ezdxf
            
            doc = ezdxf.readfile(dxf_path)
            msp = doc.modelspace()
            
            text_parts = []
            all_blocks = []
            low_confidence_regions = []
            
            # Extract TEXT and MTEXT entities
            for entity in msp:
                if entity.dxftype() == "TEXT":
                    text = entity.dxf.text
                    if text:
                        text_parts.append(text)
                        
                        # Create text block for OCR confidence tracking
                        from src.ocr.engine import TextBlock
                        block = TextBlock(
                            text=text,
                            confidence=1.0,  # Native DXF text has full confidence
                            bbox=[
                                entity.dxf.insert.x,
                                entity.dxf.insert.y,
                                entity.dxf.insert.x + entity.dxf.width,
                                entity.dxf.insert.y + entity.dxf.height,
                            ],
                            page=1,
                        )
                        all_blocks.append(block)
                
                elif entity.dxftype() == "MTEXT":
                    text = entity.text
                    if text:
                        text_parts.append(text)
                        
                        from src.ocr.engine import TextBlock
                        block = TextBlock(
                            text=text,
                            confidence=1.0,
                            bbox=[
                                entity.dxf.insert.x,
                                entity.dxf.insert.y,
                                entity.dxf.insert.x + entity.dxf.width,
                                entity.dxf.insert.y + entity.dxf.height,
                            ],
                            page=1,
                        )
                        all_blocks.append(block)
                
                # Extract ATTRIB (title block attributes)
                elif entity.dxftype() == "ATTRIB":
                    text = entity.dxf.text
                    if text:
                        text_parts.append(f"[ATTRIB:{entity.dxf.tag}]: {text}")
            
            # Extract title block information
            title_block_info = self._extract_title_block(doc)
            
            # Check if extraction is complete
            needs_ocr_fallback = len(text_parts) < 10  # Threshold for incomplete extraction
            
            if needs_ocr_fallback:
                logger.info("DXF text extraction incomplete, triggering OCR fallback")
                ocr_result = self._extract_with_ocr(dxf_path)
                text_parts.append(ocr_result["text"])
                low_confidence_regions.extend(ocr_result["low_confidence_regions"])
            
            return {
                "text": "\n".join(text_parts),
                "blocks": all_blocks,
                "low_confidence_regions": low_confidence_regions,
                "page_count": 1,
                "extraction_method": "dxf" if not needs_ocr_fallback else "dxf+ocr",
                "title_block": title_block_info,
            }
        
        except Exception as e:
            logger.error(f"DXF extraction failed: {e}", exc_info=True)
            raise IngestionError(f"DXF extraction failed: {e}") from e
    
    def _extract_title_block(self, doc) -> dict:
        """
        Extract title block information from DXF.
        
        Args:
            doc: ezdxf document object
            
        Returns:
            Dictionary with title block fields
        """
        title_block = {}
        
        try:
            # Look for title block in layout
            if hasattr(doc, 'layout'):
                for layout_name in doc.layout_names:
                    layout = doc.layout(layout_name)
                    
                    # Search for ATTRIB entities in title block
                    for entity in layout:
                        if entity.dxftype() == "ATTRIB":
                            tag = entity.dxf.tag.upper()
                            value = entity.dxf.text
                            
                            # Map common title block tags
                            if "DRAWING" in tag or "TITLE" in tag:
                                title_block["title"] = value
                            elif "NUMBER" in tag or "DWG" in tag:
                                title_block["drawing_number"] = value
                            elif "REV" in tag or "REVISION" in tag:
                                title_block["revision"] = value
                            else:
                                title_block[tag.lower()] = value
        
        except Exception as e:
            logger.warning(f"Title block extraction failed: {e}")
        
        return title_block
    
    def _extract_with_ocr(self, file_path: Path) -> dict:
        """
        Extract text using OCR fallback for CAD files.
        Uses 150 DPI (lower than standard 300 DPI for CAD drawings).
        
        Args:
            file_path: Path to CAD file
            
        Returns:
            Extraction results
        """
        try:
            # Convert to image using PyMuPDF or PIL
            image = self._render_cad_to_image(file_path, dpi=OCR_FALLBACK_DPI)
            
            # Perform OCR
            blocks = ocr_engine.ocr_image(image, page=1)
            
            # Apply confidence gating
            passing_blocks, low_conf = self.confidence_gate.evaluate(
                blocks, document_id=0
            )
            
            # Collect text
            text = "\n".join(block.text for block in passing_blocks)
            
            return {
                "text": text,
                "blocks": blocks,
                "low_confidence_regions": low_conf,
            }
        
        except Exception as e:
            logger.error(f"CAD OCR fallback failed: {e}")
            raise OCRError(f"CAD OCR fallback failed: {e}") from e
    
    def _render_cad_to_image(self, file_path: Path, dpi: int = 150) -> "Image.Image":
        """
        Render CAD file to image for OCR.
        
        Args:
            file_path: Path to CAD file
            dpi: Resolution for rendering
            
        Returns:
            PIL Image
        """
        try:
            import fitz  # PyMuPDF
            
            # Try to open as PDF first (some CAD files are PDFs)
            try:
                doc = fitz.open(file_path)
                if len(doc) > 0:
                    page = doc[0]
                    mat = fitz.Matrix(dpi / 72, dpi / 72)
                    pix = page.get_pixmap(matrix=mat)
                    img_bytes = pix.tobytes("png")
                    doc.close()
                    from PIL import Image
                    return Image.open(io.BytesIO(img_bytes))
            except Exception:
                pass
            
            # Fallback: use PIL to open image files
            from PIL import Image
            return Image.open(file_path)
        
        except ImportError:
            raise OCRError("PyMuPDF or PIL required for CAD rendering")
        except Exception as e:
            raise OCRError(f"CAD rendering failed: {e}")


# Global CAD extractor instance
cad_extractor = CADExtractor()