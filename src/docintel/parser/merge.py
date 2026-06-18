"""
Parser merge logic for DOCINTEL.
Merges deterministic and LLM extraction results into a single structured record.
"""

from typing import Any

from docintel.common.logging import get_logger
from docintel.parser.schema import StructuredRecord

logger = get_logger(__name__)


class ParserMerger:
    """
    Merges results from deterministic and LLM parsers.
    Produces a single unified StructuredRecord with confidence scoring.
    """
    
    def __init__(self):
        """Initialize the parser merger."""
        pass
    
    def merge(
        self,
        deterministic_result: dict[str, Any],
        llm_result: dict[str, Any],
        source_layer: str = "native",
    ) -> StructuredRecord:
        """
        Merge deterministic and LLM extraction results.
        
        Args:
            deterministic_result: Results from deterministic parser
            llm_result: Results from LLM extractor
            source_layer: Whether extraction was from native text or OCR
            
        Returns:
            Merged StructuredRecord
        """
        # Start with deterministic results as base
        merged = self._merge_dicts(deterministic_result, llm_result)
        
        # Calculate confidence score
        confidence = self._calculate_confidence(merged)
        
        # Determine extraction method
        extraction_method = "hybrid" if deterministic_result and llm_result else \
                          ("deterministic" if deterministic_result else "llm")
        
        # Create structured record
        try:
            record = StructuredRecord(
                document_number=merged.get("document_number"),
                title=merged.get("title"),
                revision=merged.get("revision"),
                contract_number=merged.get("contract_number"),
                issue_status=merged.get("issue_status"),
                client=merged.get("client"),
                project_title=merged.get("project_title"),
                location=merged.get("location"),
                contractor=merged.get("contractor"),
                consortium=merged.get("consortium"),
                discipline=merged.get("discipline"),
                drawing_type=merged.get("drawing_type"),
                area_code=merged.get("area_code"),
                page=merged.get("page"),
                sheet_count=merged.get("sheet_count"),
                description=merged.get("description"),
                comments=merged.get("comments", []),
                revision_history=merged.get("revision_history", []),
                legend_entries=merged.get("legend_entries", []),
                drawing_index=merged.get("drawing_index", []),
                equipment_ratings=merged.get("equipment_ratings", []),
                confidence=confidence,
                extraction_method=extraction_method,
                source_layer=source_layer,
            )
            
            logger.info(
                "Merge complete",
                extra={
                    "confidence": round(confidence, 2),
                    "method": extraction_method,
                    "doc_number": record.document_number,
                },
            )
            
            return record
            
        except Exception as e:
            logger.error(f"Failed to create merged record: {str(e)}", exc_info=True)
            raise
    
    def _merge_dicts(self, det: dict[str, Any], llm: dict[str, Any]) -> dict[str, Any]:
        """
        Merge two dictionaries, preferring non-None values.
        
        Args:
            det: Deterministic parser results
            llm: LLM parser results
            
        Returns:
            Merged dictionary
        """
        merged = det.copy()
        
        for key, llm_value in llm.items():
            if llm_value is None:
                continue
            
            det_value = merged.get(key)
            
            # Prefer deterministic for simple fields (more reliable)
            if key in ["document_number", "revision", "contract_number", "page"]:
                if det_value is None:
                    merged[key] = llm_value
            # Prefer LLM for complex fields (better context understanding)
            elif key in ["title", "project_title", "location", "description"]:
                if det_value is None or (isinstance(llm_value, str) and len(llm_value) > len(det_value or "")):
                    merged[key] = llm_value
            # For lists, combine both
            elif isinstance(llm_value, list):
                if key not in merged or not merged[key]:
                    merged[key] = llm_value
                else:
                    # Merge lists, avoiding duplicates
                    merged[key] = self._merge_lists(merged.get(key, []), llm_value)
            # For other fields, prefer non-None
            else:
                if det_value is None:
                    merged[key] = llm_value
        
        return merged
    
    def _merge_lists(self, list1: list[Any], list2: list[Any]) -> list[Any]:
        """
        Merge two lists, avoiding duplicates.
        
        Args:
            list1: First list
            list2: Second list
            
        Returns:
            Merged list
        """
        if not list1:
            return list2
        if not list2:
            return list1
        
        # For simple dicts, merge by checking if key fields match
        merged = list1.copy()
        
        for item2 in list2:
            if not isinstance(item2, dict):
                merged.append(item2)
                continue
            
            # Check if this item already exists in merged list
            is_duplicate = False
            for item1 in merged:
                if isinstance(item1, dict):
                    # Check if key fields match
                    if self._is_duplicate_item(item1, item2):
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                merged.append(item2)
        
        return merged
    
    def _is_duplicate_item(self, item1: dict, item2: dict) -> bool:
        """
        Check if two items are duplicates based on key fields.
        
        Args:
            item1: First item
            item2: Second item
            
        Returns:
            True if items are duplicates
        """
        # Check common key fields
        for key in ["comment_ref", "revision", "symbol", "drawing_number", "equipment_tag"]:
            if key in item1 and key in item2:
                if item1[key] and item2[key] and item1[key] == item2[key]:
                    return True
        return False
    
    def _calculate_confidence(self, merged: dict[str, Any]) -> float:
        """
        Calculate confidence score for merged result.
        
        Args:
            merged: Merged extraction results
            
        Returns:
            Confidence score (0-1)
        """
        # Key fields that indicate good extraction
        key_fields = [
            "document_number",
            "title",
            "revision",
            "contract_number",
            "client",
            "page",
        ]
        
        fields_found = sum(1 for f in key_fields if merged.get(f) is not None)
        key_field_score = fields_found / len(key_fields)
        
        # Bonus for structured tables
        table_fields = ["comments", "revision_history", "legend_entries", "drawing_index", "equipment_ratings"]
        tables_found = sum(1 for f in table_fields if merged.get(f) and len(merged[f]) > 0)
        table_score = min(tables_found / len(table_fields), 1.0)
        
        # Weighted combination
        confidence = (key_field_score * 0.7) + (table_score * 0.3)
        
        return min(confidence, 1.0)


# Global merger instance
_merger: ParserMerger | None = None


def get_parser_merger() -> ParserMerger:
    """Get the global parser merger instance."""
    global _merger
    if _merger is None:
        _merger = ParserMerger()
    return _merger