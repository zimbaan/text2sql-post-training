"""LLM clients (Ollama and OpenRouter) for NL→SQL generation."""

import json
import logging
from typing import Any, Dict, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class JSONExtractorMixin:
    """Shared JSON extraction helpers."""

    def _extract_json(self, text: str) -> Optional[str]:
        """Extract JSON from text, handling markdown code blocks or plain JSON."""
        text = text.strip()

        import re

        # Look for ```json ... ``` or ``` ... ```
        json_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_block_match:
            return json_block_match.group(1)

        # Look for JSON object at start or anywhere
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            candidate = json_match.group(0)
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                pass

        # If text looks like JSON itself
        if text.startswith("{") and text.endswith("}"):
            try:
                json.loads(text)
                return text
            except json.JSONDecodeError:
                pass

        return None


class BaseLLMClient(JSONExtractorMixin):
    """Base LLM client with JSON utilities."""

    default_model: str

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        format_json: bool = False,
    ) -> str:
        raise NotImplementedError

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        retry_on_failure: bool = True,
    ) -> Dict[str, Any]:
        """Generate JSON response using the underlying provider."""
        try:
            response = await self.generate(
                prompt,
                model=model,
                system_prompt=system_prompt,
                format_json=True,
            )
        except Exception as e:
            raise ValueError(f"Failed to generate response from LLM: {e}") from e

        json_text = self._extract_json(response)

        if not json_text and retry_on_failure:
            json_prompt = f"{prompt}\n\nIMPORTANT: Return ONLY valid JSON, no prose or markdown."
            response = await self.generate(
                json_prompt,
                model=model,
                system_prompt=system_prompt,
                format_json=True,
            )
            json_text = self._extract_json(response)

        if not json_text:
            raise ValueError(
                f"Could not extract JSON from LLM response. Response was: {response[:200]}"
            )

        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON from LLM: {e}\nExtracted text: {json_text[:500]}"
            ) from e

    async def list_models(self) -> list[Dict[str, Any]]:
        """List available models for the provider."""
        return []

    async def close(self):
        """Close underlying HTTP client if needed."""
        pass


class OllamaClient(BaseLLMClient):
    """Client for interacting with Ollama API."""

    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or settings.ollama_base_url
        self.default_model = model or settings.default_ollama_model
        self.client = httpx.AsyncClient(timeout=120.0)

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        format_json: bool = False,
    ) -> str:
        model = model or self.default_model
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        if format_json:
            payload["format"] = "json"

        if system_prompt:
            payload["system"] = system_prompt

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to Ollama at {self.base_url}: {e}")
            raise ValueError(f"Cannot connect to Ollama server at {self.base_url}") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API error: {e.response.status_code} - {e.response.text}")
            raise

    async def list_models(self) -> list[Dict[str, Any]]:
        url = f"{self.base_url}/api/tags"
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to Ollama at {self.base_url}: {e}")
            raise ValueError(f"Cannot connect to Ollama server at {self.base_url}") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API error: {e.response.status_code}")
            raise

    async def close(self):
        await self.client.aclose()


class OpenRouterClient(BaseLLMClient):
    """OpenRouter (OpenAI-compatible) client for hosted models."""

    def __init__(self, base_url: str = None, model: str = None, api_key: Optional[str] = None):
        self.base_url = base_url or settings.openrouter_base_url
        self.default_model = model or settings.openrouter_model
        self.api_key = api_key or settings.openrouter_api_key
        self.client = httpx.AsyncClient(timeout=120.0)

    def _build_headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise ValueError("OpenRouter API key is not configured (OPENROUTER_API_KEY).")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        format_json: bool = False,
    ) -> str:
        model = model or self.default_model
        url = f"{self.base_url}/chat/completions"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        if format_json:
            payload["response_format"] = {"type": "json_object"}

        headers = self._build_headers()

        try:
            response = await self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                raise ValueError("No choices returned from OpenRouter.")
            return choices[0].get("message", {}).get("content", "").strip()
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to OpenRouter at {self.base_url}: {e}")
            raise ValueError(f"Cannot connect to OpenRouter at {self.base_url}") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")
            raise

    async def list_models(self) -> list[Dict[str, Any]]:
        url = f"{self.base_url}/models"
        headers = self._build_headers()
        try:
            response = await self.client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            models_data = data.get("data", []) or data.get("models", [])
            models: list[Dict[str, Any]] = []
            for item in models_data:
                name = item.get("id") or item.get("name") or ""
                if name:
                    models.append({"name": name})
            if not models and self.default_model:
                models.append({"name": self.default_model})
            return models
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to OpenRouter at {self.base_url}: {e}")
            raise ValueError(f"Cannot connect to OpenRouter at {self.base_url}") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")
            raise

    async def close(self):
        await self.client.aclose()


# Global client instances
_ollama_client: Optional[OllamaClient] = None
_llm_client: Optional[BaseLLMClient] = None


def get_ollama_client() -> OllamaClient:
    """Get or create global Ollama client instance."""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client


def get_llm_client() -> BaseLLMClient:
    """Return the configured LLM client based on LLM_PROVIDER."""
    global _llm_client
    if _llm_client is not None:
        return _llm_client

    provider = settings.llm_provider.lower()
    if provider == "ollama":
        _llm_client = get_ollama_client()
    elif provider in ("openrouter", "openai"):
        # OpenRouter is OpenAI-compatible; reuse the same client shape.
        base_url = settings.openrouter_base_url if provider == "openrouter" else settings.openai_base_url
        model = settings.openrouter_model if provider == "openrouter" else settings.openai_model
        api_key = settings.openrouter_api_key if provider == "openrouter" else settings.openai_api_key
        _llm_client = OpenRouterClient(base_url=base_url, model=model, api_key=api_key)
    else:
        logger.warning(f"Unknown LLM_PROVIDER '{provider}', defaulting to Ollama.")
        _llm_client = get_ollama_client()

    return _llm_client
