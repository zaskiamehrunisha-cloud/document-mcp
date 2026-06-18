"""
DXF extractor for DOCINTEL.
Extracts text and metadata from DXF files using ezdxf.
"""

from pathlib import Path
from typing import Optional

import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.properties import LayoutProperties

from docintel.common.exceptions import ExtractionError
from docintel.common.logging import get_logger
from docintel.common.constants import SOURCE_LAYER_NATIVE

logger = get_logger(__name__)


class DXFExtractor:
    """
    Extracts text and metadata from DXF files.
    Uses ezdxf for reading DXF format CAD drawings.
    """
    
    def __init__(self):
        """Initialize the DXF extractor."""
        pass
    
    def extract(self, file_path: str) -> dict:
        """
        Extract text and metadata from a DXF file.
        
        Args:
            file_path: Path to the DXF file
            
        Returns:
            Dictionary with 'text', 'metadata', and 'source_layer'
        """
        try:
            doc = ezdxf.readfile(file_path)
            msp = doc.modelspace()
            
            # Extract metadata
            metadata = self._extract_metadata(doc)
            
            # Extract text from all entities
            text_parts = []
            
            # Extract from model space
            for entity in msp:
                text = self._extract_entity_text(entity)
                if text:
                    text_parts.append(text)
            
            # Also check paper space (layouts)
            for layout_name in doc.layout_names:
                if layout_name == "Model":
                    continue
                layout = doc.layouts.get(layout_name)
                for entity in layout:
                    text = self._extract_entity_text(entity)
                    if text:
                        text_parts.append(f"[{layout_name}] {text}")
            
            full_text = "\n".join(text_parts)
            
            logger.info(
                "DXF extraction complete",
                extra={
                    "file": file_path,
                    "entities": len(text_parts),
                    "total_chars": len(full_text),
                },
            )
            
            return {
                "text": full_text,
                "metadata": metadata,
                "source_layer": SOURCE_LAYER_NATIVE,
            }
            
        except Exception as e:
            error_msg = f"Failed to extract DXF: {str(e)}"
            logger.error(error_msg, extra={"file": file_path}, exc_info=True)
            raise ExtractionError(error_msg) from e
    
    def _extract_entity_text(self, entity) -> Optional[str]:
        """
        Extract text from a DXF entity.
        
        Args:
            entity: ezdxf entity object
            
        Returns:
            Extracted text or None
        """
        try:
            entity_type = entity.dxftype()
            
            # TEXT and MTEXT entities
            if entity_type in ["TEXT", "MTEXT"]:
                return entity.text if hasattr(entity, "text") else entity.raw_text
            
            # ATTRIB and ATTDEF (attributes in blocks)
            if entity_type in ["ATTRIB", "ATTDEF"]:
                return entity.text if hasattr(entity, "text") else None
            
            # DIMENSION entities
            if entity_type.startswith("DIM"):
                return self._extract_dimension_text(entity)
            
            # LEADER (leaders with text)
            if entity_type == "LEADER":
                return None  # Complex, skip for now
            
            # MLEADER (multileaders)
            if entity_type == "MLEADER":
                return None  # Complex, skip for now
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not extract text from {entity.dxftype()}: {str(e)}")
            return None
    
    def _extract_dimension_text(self, entity) -> Optional[str]:
        """Extract text from dimension entities."""
        try:
            if hasattr(entity, "text"):
                return entity.text
            elif hasattr(entity, "dimension_text"):
                return entity.dimension_text
            return None
        except Exception:
            return None
    
    def _extract_metadata(self, doc: ezdxf.Document) -> dict:
        """
        Extract metadata from a DXF document.
        
        Args:
            doc: ezdxf document object
            
        Returns:
            Dictionary of metadata
        """
        metadata = {}
        
        try:
            # Get header variables
            header = doc.header
            
            # Extract common metadata
            if "$INSUNITS" in header:
                metadata["units"] = header["$INSUNITS"]
            
            if "$EXTMIN" in header and "$EXTMAX" in header:
                ext_min = header["$EXTMIN"]
                ext_max = header["$EXTMAX"]
                metadata["extents"] = {
                    "min_x": ext_min.x if hasattr(ext_min, "x") else ext_min[0],
                    "min_y": ext_min.y if hasattr(ext_min, "y") else ext_min[1],
                    "max_x": ext_max.x if hasattr(ext_max, "x") else ext_max[0],
                    "max_y": ext_max.y if hasattr(ext_max, "y") else ext_max[1],
                }
            
            # Get layer count
            layers = list(doc.layers)
            metadata["layer_count"] = len(layers)
            metadata["layers"] = [layer.dxf.name for layer in layers[:20]]  # First 20
            
            # Get block count
            blocks = list(doc.blocks)
            metadata["block_count"] = len(blocks)
            
            # Try to extract title block info from model space
            msp = doc.modelspace()
            metadata["entity_count"] = len(list(msp))
            
        except Exception as e:
            logger.warning(f"Could not extract all DXF metadata: {str(e)}")
        
        return metadata
    
    def extract_page(self, file_path: str, page_number: int) -> dict:
        """
        DXF files don't have pages, but we support this for consistency.
        Returns the full extraction.
        
        Args:
            file_path: Path to the DXF file
            page_number: Ignored for DXF
            
        Returns:
            Dictionary with 'text' and 'metadata'
        """
        return self.extract(file_path)
    
    def get_entity_count(self, file_path: str) -> int:
        """
        Get the number of entities in a DXF file.
        
        Args:
            file_path: Path to the DXF file
            
        Returns:
            Number of entities
        """
        try:
            doc = ezdxf.readfile(file_path)
            msp = doc.modelspace()
            return len(list(msp))
        except Exception as e:
            error_msg = f"Failed to count entities: {str(e)}"
            logger.error(error_msg, extra={"file": file_path})
            raise ExtractionError(error_msg) from e
    
    def get_layers(self, file_path: str) -> list[str]:
        """
        Get all layer names in a DXF file.
        
        Args:
            file_path: Path to the DXF file
            
        Returns:
            List of layer names
        """
        try:
            doc = ezdxf.readfile(file_path)
            return [layer.dxf.name for layer in doc.layers]
        except Exception as e:
            error_msg = f"Failed to get layers: {str(e)}"
            logger.error(error_msg, extra={"file": file_path})
            raise ExtractionError(error_msg) from e


# Global DXF extractor instance
_dxf_extractor: Optional[DXFExtractor] = None


def get_dxf_extractor() -> DXFExtractor:
    """Get the global DXF extractor instance."""
    global _dxf_extractor
    if _dxf_extractor is None:
        _dxf_extractor = DXFExtractor()
    return _dxf_extractor