"""Merge deterministic and LLM extraction results."""
import logging
from typing import Optional

from src.parser.deterministic import ParsedDocument
from src.common.exceptions import ParseError

logger = logging.getLogger(__name__)


class ExtractionMerger:
    """
    Merges deterministic parser results with LLM extraction results.
    Deterministic results take precedence for core fields; LLM augments
    with free-text and complex extractions.
    """
    
    def merge(
        self,
        deterministic: ParsedDocument,
        llm_result: dict,
    ) -> ParsedDocument:
        """
        Merge deterministic and LLM extraction results.
        
        Args:
            deterministic: Results from deterministic parser
            llm_result: Results from LLM extraction (dict)
            
        Returns:
            Merged ParsedDocument
        """
        try:
            # Core fields: deterministic takes precedence
            # (LLM results are not used for these)
            
            # Augment with LLM results for free-text fields
            
            # Merge general notes
            if llm_result.get("general_notes"):
                deterministic.extraction_metadata["general_notes"] = llm_result["general_notes"]
            
            # Merge equipment ratings (LLM may find more)
            llm_equipment = llm_result.get("equipment_details", [])
            if llm_equipment:
                # Add LLM equipment not already in deterministic results
                existing_tags = {r.get("tag") for r in deterministic.equipment_ratings}
                for equipment in llm_equipment:
                    tag = equipment.get("tag")
                    if tag and tag not in existing_tags:
                        deterministic.equipment_ratings.append(equipment)
            
            # Merge legend symbols (LLM may find more)
            llm_legend = llm_result.get("legend_descriptions", [])
            if llm_legend:
                existing_symbols = {s.get("symbol") for s in deterministic.legend_symbols}
                for symbol in llm_legend:
                    sym = symbol.get("symbol")
                    if sym and sym not in existing_symbols:
                        deterministic.legend_symbols.append(symbol)
            
            # Merge complex comments (LLM handles nested text better)
            llm_comments = llm_result.get("complex_comments", [])
            if llm_comments:
                # Use LLM comments if deterministic didn't find any
                if not deterministic.comments:
                    deterministic.comments = [
                        {
                            "seq": i + 1,
                            "client_comment": c.get("comment"),
                            "contractor_response": c.get("response"),
                        }
                        for i, c in enumerate(llm_comments)
                    ]
            
            # Merge specifications
            if llm_result.get("specifications"):
                deterministic.extraction_metadata["specifications"] = llm_result["specifications"]
            
            # Update metadata
            deterministic.extraction_metadata["parser"] = "deterministic+llm"
            deterministic.extraction_metadata["llm_fields_added"] = self._count_llm_additions(
                deterministic, llm_result
            )
            
            logger.info(
                f"Merge complete: {deterministic.extraction_metadata.get('fields_extracted', 0)} "
                f"deterministic fields + {deterministic.extraction_metadata.get('llm_fields_added', 0)} LLM augmentations"
            )
            
            return deterministic
            
        except Exception as e:
            logger.error(f"Merge failed: {e}", exc_info=True)
            raise ParseError(f"Failed to merge extraction results: {e}") from e
    
    def _count_llm_additions(self, deterministic: ParsedDocument, llm_result: dict) -> int:
        """Count how many fields were added by LLM."""
        count = 0
        
        if llm_result.get("general_notes"):
            count += len(llm_result["general_notes"])
        
        if llm_result.get("equipment_details"):
            existing_tags = {r.get("tag") for r in deterministic.equipment_ratings}
            for eq in llm_result["equipment_details"]:
                if eq.get("tag") not in existing_tags:
                    count += 1
        
        if llm_result.get("legend_descriptions"):
            existing_symbols = {s.get("symbol") for s in deterministic.legend_symbols}
            for sym in llm_result["legend_descriptions"]:
                if sym.get("symbol") not in existing_symbols:
                    count += 1
        
        if llm_result.get("complex_comments") and not deterministic.comments:
            count += len(llm_result["complex_comments"])
        
        if llm_result.get("specifications"):
            count += len(llm_result["specifications"])
        
        return count


# Global merger instance
extraction_merger = ExtractionMerger()