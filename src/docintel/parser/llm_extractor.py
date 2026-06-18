"""
LLM-based extractor for DOCINTEL.
Uses local LLM to extract structured information from document text.
"""

import json
import re
from typing import Any

from docintel.common.exceptions import LLMInferenceError, ParseError
from docintel.common.logging import get_logger
from docintel.llm.local_client import get_llm_client
from docintel.parser.schema import StructuredRecord

logger = get_logger(__name__)


class LLMExtractor:
    """
    Uses local LLM to extract structured fields from document text.
    Complements the deterministic parser with LLM-based extraction.
    """
    
    def __init__(self):
        """Initialize the LLM extractor."""
        self.llm_client = get_llm_client()
    
    async def extract(self, text: str, max_chars: int = 8000) -> dict[str, Any]:
        """
        Extract structured information using LLM.
        
        Args:
            text: Raw text from document
            max_chars: Maximum characters to send to LLM (truncate if longer)
            
        Returns:
            Dictionary of extracted fields
        """
        try:
            # Truncate text if too long
            if len(text) > max_chars:
                text = text[:max_chars] + "\n...[truncated]"
            
            # Build prompt
            prompt = self._build_extraction_prompt(text)
            
            # Call LLM
            response = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=2000,
            )
            
            # Parse JSON response
            result = self._parse_llm_response(response)
            
            logger.info(
                "LLM extraction complete",
                extra={
                    "fields_extracted": len([k for v in result.values() if v is not None]),
                },
            )
            
            return result
            
        except LLMInferenceError:
            raise
        except Exception as e:
            error_msg = f"LLM extraction failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ParseError(error_msg) from e
    
    def _build_extraction_prompt(self, text: str) -> str:
        """Build the extraction prompt for the LLM."""
        return f"""Extract structured information from this engineering document text.
Return a JSON object with these fields (use null for missing fields):

{{
  "document_number": "string (format: XXX-X-XX-XX-XXX)",
  "title": "string",
  "revision": "string (single character or code like ASB, IFI)",
  "contract_number": "string",
  "issue_status": "string (IFR, IFA, IFC, ASB, IFI, or similar)",
  "client": "string",
  "project_title": "string",
  "location": "string",
  "drawing_type": "string",
  "discipline": "string (single letter code)",
  "page": "string (e.g., 'Page 1 of 5')",
  "sheet_count": "integer or null",
  "description": "string",
  "comments": [array of objects with comment_ref, comment_text, response_text, status],
  "revision_history": [array of objects with revision, date, description],
  "legend_entries": [array of objects with symbol, description],
  "drawing_index": [array of objects with drawing_number, drawing_title, revision, sheet_count],
  "equipment_ratings": [array of objects with equipment_tag, parameter, value, unit]
}}

Document text:
{text}

Return ONLY valid JSON, no markdown formatting or explanations."""
    
    def _parse_llm_response(self, response: str) -> dict[str, Any]:
        """
        Parse the LLM response to extract JSON.
        
        Args:
            response: Raw LLM response text
            
        Returns:
            Parsed dictionary
        """
        try:
            # Try to find JSON in the response
            # Look for JSON object pattern
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            
            # If no JSON found, try parsing the whole response
            return json.loads(response)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Could not parse LLM response as JSON: {str(e)}")
            logger.debug(f"LLM response: {response[:500]}")
            return {}
    
    async def extract_structured_record(self, text: str) -> StructuredRecord:
        """
        Extract a complete StructuredRecord using LLM.
        
        Args:
            text: Raw text from document
            
        Returns:
            StructuredRecord object
        """
        result = await self.extract(text)
        
        try:
            return StructuredRecord(
                document_number=result.get("document_number"),
                title=result.get("title"),
                revision=result.get("revision"),
                contract_number=result.get("contract_number"),
                issue_status=result.get("issue_status"),
                client=result.get("client"),
                project_title=result.get("project_title"),
                location=result.get("location"),
                drawing_type=result.get("drawing_type"),
                discipline=result.get("discipline"),
                page=result.get("page"),
                sheet_count=result.get("sheet_count"),
                description=result.get("description"),
                comments=result.get("comments", []),
                revision_history=result.get("revision_history", []),
                legend_entries=result.get("legend_entries", []),
                drawing_index=result.get("drawing_index", []),
                equipment_ratings=result.get("equipment_ratings", []),
                confidence=0.7,  # LLM extraction gets moderate confidence
                extraction_method="llm",
                source_layer="native",
            )
        except Exception as e:
            logger.error(f"Failed to create StructuredRecord: {str(e)}")
            raise ParseError(f"Failed to create structured record: {str(e)}") from e


# Global LLM extractor instance
_llm_extractor: LLMExtractor | None = None


def get_llm_extractor() -> LLMExtractor:
    """Get the global LLM extractor instance."""
    global _llm_extractor
    if _llm_extractor is None:
        _llm_extractor = LLMExtractor()
    return _llm_extractor