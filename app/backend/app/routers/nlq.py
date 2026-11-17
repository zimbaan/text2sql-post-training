"""Natural Language Query router."""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import get_settings
from app.core.finetuned import get_finetuned_model
from app.core.llm import get_llm_client
from app.core.dependencies import get_current_active_user
from app.models.dtos import (
    ModelInfo,
    ModelsResponse,
    NLQExplainResponse,
    NLQRequest,
    NLQResponse,
    QueryHistoryEntry,
    QueryHistoryResponse,
)
from app.services.nl2sql import get_nl2sql_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/nlq", tags=["NLQ"])
settings = get_settings()


@router.post("/{connection_id}", response_model=NLQResponse)
async def execute_nlq(
    connection_id: str,
    request: NLQRequest,
    current_user = Depends(get_current_active_user),
) -> NLQResponse:
    """Convert natural language to SQL and execute.

    Args:
        connection_id: Connection identifier
        request: NLQ request with user query and options

    Returns:
        NLQ response with SQL and results

    Raises:
        HTTPException: If connection not found or query fails
    """
    try:
        service = get_nl2sql_service()
        result = await service.generate_sql(
            connection_id=connection_id,
            user_query=request.user_query,
            database=request.database,
            schema=request.schema,
            table_scope=request.table_scope,
            allow_modification=request.allow_modification,
            return_sql_only=request.return_sql_only,
            confirm_execution=request.confirm_execution,
            user_id=current_user.id,
            model=request.llm,
        )

        return NLQResponse(**result)
    except ValueError as e:
        logger.error(f"NLQ failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "NLQ_FAILED",
                    "message": str(e),
                    "details": None,
                }
            },
        )
    except Exception as e:
        logger.error(f"Unexpected error in NLQ: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to process NLQ",
                    "details": {"error": str(e)},
                }
            },
        )


@router.post("/explain/{connection_id}", response_model=NLQExplainResponse)
async def explain_nlq(
    connection_id: str,
    request: NLQRequest,
    current_user = Depends(get_current_active_user),
) -> NLQExplainResponse:
    """Convert natural language to SQL without executing.

    Args:
        connection_id: Connection identifier
        request: NLQ request with user query

    Returns:
        NLQ explain response with SQL and reasoning

    Raises:
        HTTPException: If connection not found or query fails
    """
    try:
        service = get_nl2sql_service()
        result = await service.generate_sql(
            connection_id=connection_id,
            user_query=request.user_query,
            database=request.database,
            schema=request.schema,
            table_scope=request.table_scope,
            allow_modification=request.allow_modification,
            return_sql_only=True,
            user_id=current_user.id,
            model=request.llm,
        )

        return NLQExplainResponse(
            sql=result["sql"],
            original_sql=result.get("original_sql"),
            parameters=result.get("parameters", {}),
            reasoning=result.get("reasoning", ""),
            is_read_only=result.get("is_read_only", True),
            limit_applied=result.get("limit_applied", False),
            confidence=result.get("confidence", 0.0),
            warnings=result.get("warnings", []),
            generated_by=result.get("generated_by"),
        )
    except ValueError as e:
        logger.error(f"NLQ explain failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "NLQ_FAILED",
                    "message": str(e),
                    "details": None,
                }
            },
        )
    except Exception as e:
        logger.error(f"Unexpected error in NLQ explain: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to explain NLQ",
                    "details": {"error": str(e)},
                }
            },
        )


@router.get("/models", response_model=ModelsResponse)
async def list_models() -> ModelsResponse:
    """List the post-trained text-to-SQL model (if installed) and the configured provider's models."""
    finetuned = get_finetuned_model()
    try:
        llm_client = get_llm_client()
        provider = settings.llm_provider.lower()
        default_model = getattr(llm_client, "default_model", None)
        if not default_model:
            if provider == "ollama":
                default_model = settings.default_ollama_model
            elif provider in ("openrouter", "openai"):
                default_model = settings.openrouter_model if provider == "openrouter" else settings.openai_model

        try:
            models = await llm_client.list_models()
        except ValueError:
            # Provider unreachable (e.g. Ollama not running): still offer the fine-tuned model.
            if finetuned is None:
                raise
            logger.warning("LLM provider unavailable; listing only the fine-tuned model")
            models, default_model = [], finetuned.name

        model_infos = []
        if finetuned is not None:
            model_infos.append(
                ModelInfo(name=finetuned.name, is_default=finetuned.name == default_model, is_finetuned=True)
            )
        for model in models:
            name = model.get("name", "") or model.get("id", "")
            if not name or (finetuned is not None and name == finetuned.name):
                continue
            model_infos.append(ModelInfo(name=name, is_default=name == default_model))

        if not model_infos and default_model:
            model_infos.append(ModelInfo(name=default_model, is_default=True))

        return ModelsResponse(models=model_infos, default_model=default_model or "")
    except ValueError as e:
        logger.error(f"Failed to list models: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": {
                    "code": "LLM_UNAVAILABLE",
                    "message": str(e),
                    "details": None,
                }
            },
        )
    except Exception as e:
        logger.error(f"Unexpected error listing models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Failed to list models",
                    "details": {"error": str(e)},
                }
            },
        )


@router.get("/history/{connection_id}", response_model=QueryHistoryResponse)
async def get_history(connection_id: str) -> QueryHistoryResponse:
    """Get query history for a connection.

    Args:
        connection_id: Connection identifier

    Returns:
        Query history response

    Raises:
        HTTPException: If connection not found
    """
    service = get_nl2sql_service()
    history = service.get_history(connection_id)

    return QueryHistoryResponse(
        queries=[
            QueryHistoryEntry(
                timestamp=entry["timestamp"],
                user_query=entry["user_query"],
                sql=entry["sql"],
                row_count=entry["row_count"],
                duration_ms=entry["duration_ms"],
                warnings=entry.get("warnings", []),
                confidence=entry.get("confidence", 0.0),
            )
            for entry in history
        ]
    )

