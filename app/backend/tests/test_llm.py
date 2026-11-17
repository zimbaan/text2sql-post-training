"""Tests for LLM client."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.llm import OllamaClient


@pytest.mark.asyncio
async def test_extract_json():
    """Test JSON extraction from text."""
    client = OllamaClient()

    # Test plain JSON
    text = '{"sql": "SELECT * FROM users", "reasoning": "test"}'
    result = client._extract_json(text)
    assert result == text

    # Test JSON in markdown code block
    text = '```json\n{"sql": "SELECT * FROM users"}\n```'
    result = client._extract_json(text)
    assert '"sql"' in result

    # Test JSON with prose
    text = 'Here is the result:\n{"sql": "SELECT * FROM users"}'
    result = client._extract_json(text)
    assert result is not None
    parsed = json.loads(result)
    assert "sql" in parsed

    # Test invalid text
    text = "This is not JSON at all"
    result = client._extract_json(text)
    assert result is None


@pytest.mark.asyncio
async def test_generate_json():
    """Test JSON generation (mocked)."""
    client = OllamaClient()

    # Mock the generate method
    with patch.object(client, "generate", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = '{"sql": "SELECT * FROM users", "confidence": 0.9}'

        result = await client.generate_json("test prompt")
        assert "sql" in result
        assert result["confidence"] == 0.9

