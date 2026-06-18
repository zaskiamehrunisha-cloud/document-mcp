"""
Local LLM client for DOCINTEL.
Provides a unified interface to Ollama/vLLM with offline guard enforcement.
All inference goes through this client - no direct HTTP calls elsewhere.
"""

import json
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from docintel.common.exceptions import LLMInferenceError, OfflineGuardViolationError
from docintel.common.logging import get_logger
from docintel.config.settings import settings
from docintel.llm.guards import validate_url

logger = get_logger(__name__)


class LocalLLMClient:
    """
    Client for local LLM inference (Ollama/vLLM).
    Enforces offline guard on all requests.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """
        Initialize the local LLM client.
        
        Args:
            base_url: Base URL of the LLM server (e.g., "http://localhost:11434/v1")
            api_key: API key (Ollama accepts any key)
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        """
        self.base_url = base_url or settings.llm_base_url
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model
        self.temperature = temperature if temperature is not None else settings.llm_temperature
        self.max_tokens = max_tokens if max_tokens is not None else settings.llm_max_tokens
        
        # Validate the base URL against offline guard
        validate_url(self.base_url)
        
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=httpx.Timeout(
                    connect=10.0,
                    read=120.0,
                    write=10.0,
                    pool=10.0,
                ),
            )
        return self._client
    
    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[List[str]] = None,
    ) -> str:
        """
        Generate a completion from the LLM.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max tokens
            stop_sequences: Optional list of stop sequences
            
        Returns:
            The generated text
            
        Raises:
            LLMInferenceError: If generation fails
            OfflineGuardViolationError: If the base URL is not local
        """
        client = await self._get_client()
        
        # Build the messages list
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Build the request body
        body: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            "stream": False,
        }
        if stop_sequences:
            body["stop"] = stop_sequences
        
        logger.debug(
            "LLM generate request",
            extra={"model": self.model, "prompt_length": len(prompt)},
        )
        
        start_time = time.time()
        
        try:
            response = await client.post("/chat/completions", json=body)
            response.raise_for_status()
            
            data = response.json()
            generated_text = data["choices"][0]["message"]["content"]
            
            elapsed = time.time() - start_time
            logger.info(
                "LLM generate complete",
                extra={
                    "model": self.model,
                    "elapsed_seconds": round(elapsed, 2),
                    "response_length": len(generated_text),
                },
            )
            
            return generated_text
            
        except httpx.HTTPStatusError as e:
            error_msg = f"LLM API error: {e.response.status_code} - {e.response.text}"
            logger.error(error_msg, extra={"status_code": e.response.status_code})
            raise LLMInferenceError(error_msg) from e
            
        except httpx.TimeoutException as e:
            error_msg = f"LLM request timed out after {self.max_tokens} seconds"
            logger.error(error_msg)
            raise LLMInferenceError(error_msg) from e
            
        except Exception as e:
            error_msg = f"LLM inference failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise LLMInferenceError(error_msg) from e
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming completion from the LLM.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max tokens
            
        Yields:
            Chunks of generated text
        """
        client = await self._get_client()
        
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        body: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            "stream": True,
        }
        
        try:
            async with client.stream("POST", "/chat/completions", json=body) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            error_msg = f"LLM streaming failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise LLMInferenceError(error_msg) from e
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.debug("LLM client closed")
    
    async def __aenter__(self) -> "LocalLLMClient":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()


# Global LLM client instance
_llm_client: Optional[LocalLLMClient] = None


def get_llm_client() -> LocalLLMClient:
    """Get the global LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LocalLLMClient()
    return _llm_client