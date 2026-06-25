"""LLM-based extraction using local Ollama for free-text and complex fields."""
import json
import logging
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import settings
from src.common.exceptions import LLMError
from src.common.constants import EMBEDDING_MODEL

logger = logging.getLogger(__name__)


class LLMExtractor:
    """
    LLM extraction pass using local Ollama.
    Handles free-text general notes, equipment ratings, legend descriptions,
    and complex nested comment text. Returns JSON only with single retry on failure.
    """
    
    def __init__(self):
        """Initialize LLM extractor."""
        self.ollama_host = settings.ollama_host
        self.model = settings.ollama_model
        self.fallback_model = settings.ollama_fallback_model
    
    async def extract(self, text: str, context: Optional[dict] = None) -> dict:
        """
        Extract structured data from text using LLM.
        
        Args:
            text: Text content to extract from
            context: Optional context (document type, discipline, etc.)
            
        Returns:
            Dictionary with extracted fields
        """
        import httpx
        
        prompt = self._build_extraction_prompt(text, context)
        
        try:
            result = await self._call_ollama(prompt)
            return self._parse_llm_response(result)
        except Exception as e:
            logger.warning(f"Primary LLM extraction failed: {e}. Trying fallback model.")
            try:
                result = await self._call_ollama(prompt, use_fallback=True)
                return self._parse_llm_response(result)
            except Exception as e2:
                logger.error(f"LLM extraction failed completely: {e2}")
                raise LLMError(f"LLM extraction failed: {e2}") from e2
    
    def _build_extraction_prompt(self, text: str, context: Optional[dict]) -> str:
        """
        Build extraction prompt for the LLM.
        
        Args:
            text: Text to extract from
            context: Optional context
            
        Returns:
            Formatted prompt string
        """
        context_str = ""
        if context:
            context_str = f"\nContext: {json.dumps(context)}"
        
        # Truncate text if too long (keep first 8000 chars for LLM context)
        text_truncated = text[:8000] if len(text) > 8000 else text
        
        prompt = f"""You are an engineering document parser. Extract structured data from the following engineering document text and return ONLY valid JSON.

Extract the following fields if present:
- general_notes: Array of general notes and remarks
- equipment_details: Array of objects with tag, description, rating, voltage, phase, frequency, power
- legend_descriptions: Array of objects with symbol and description
- complex_comments: Array of objects with comment and response
- specifications: Array of technical specifications found

Document Text:
{text_truncated}
Example format:
{{
  "general_notes": ["Note 1", "Note 2"],
  "equipment_details": [{{"tag": "ARG-E-OD-00-006", "description": "Portable Generator", "rating": "2 kW", "voltage": "230 VAC", "phase": "1-phase", "frequency": "50 Hz", "power": "2 kW"}}],
  "legend_descriptions": [{{"symbol": "M", "description": "Motor"}}],
  "complex_comments": [{{"comment": "Comment text", "response": "Response text"}}],
  "specifications": ["Spec 1", "Spec 2"]
}}

If a field is not found, return an empty array. Return ONLY the JSON object."""
        
        return prompt
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _call_ollama(self, prompt: str, use_fallback: bool = False) -> str:
        """
        Call Ollama API with the given prompt.
        
        Args:
            prompt: Prompt text
            use_fallback: Whether to use fallback model
            
        Returns:
            LLM response text
        """
        import httpx
        
        model = self.fallback_model if use_fallback else self.model
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",  # Request JSON output
                    "options": {
                        "temperature": 0.1,  # Low temperature for deterministic output
                        "num_predict": 2000,
                    },
                },
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
    
    def _parse_llm_response(self, response: str) -> dict:
        """
        Parse LLM response and extract JSON.
        
        Args:
            response: Raw LLM response
            
        Returns:
            Parsed JSON dictionary
            
        Raises:
            LLMError: If response cannot be parsed as JSON
        """
        try:
            # Try to extract JSON from response (handle markdown code blocks)
            response = response.strip()
            
            # Remove markdown code blocks if present
            if response.startswith("```"):
                lines = response.split("\n")
                # Remove first and last lines (``` markers)
                response = "\n".join(lines[1:-1])
            
            # Parse JSON
            data = json.loads(response)
            
            # Validate structure
            if not isinstance(data, dict):
                raise ValueError("Response is not a JSON object")
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Raw response: {response}")
            raise LLMError(f"LLM returned invalid JSON: {e}") from e
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            raise LLMError(f"LLM response parsing failed: {e}") from e
    
    async def extract_equipment_ratings(self, text: str) -> list[dict]:
        """
        Extract equipment ratings using LLM.
        
        Args:
            text: Text content
            
        Returns:
            List of equipment rating dictionaries
        """
        result = await self.extract(text, context={"task": "extract_equipment_ratings"})
        return result.get("equipment_details", [])
    
    async def extract_legend_symbols(self, text: str) -> list[dict]:
        """
        Extract legend symbols using LLM.
        
        Args:
            text: Text content
            
        Returns:
            List of legend symbol dictionaries
        """
        result = await self.extract(text, context={"task": "extract_legend_symbols"})
        return result.get("legend_descriptions", [])
    
    async def extract_general_notes(self, text: str) -> list[str]:
        """
        Extract general notes using LLM.
        
        Args:
            text: Text content
            
        Returns:
            List of general notes
        """
        result = await self.extract(text, context={"task": "extract_general_notes"})
        return result.get("general_notes", [])
    
    async def extract_complex_comments(self, text: str) -> list[dict]:
        """
        Extract complex comment/response pairs using LLM.
        
        Args:
            text: Text content
            
        Returns:
            List of comment/response dictionaries
        """
        result = await self.extract(text, context={"task": "extract_comments"})
        return result.get("complex_comments", [])


# Global LLM extractor instance
llm_extractor = LLMExtractor()