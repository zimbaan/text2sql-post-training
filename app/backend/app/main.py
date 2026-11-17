"""FastAPI application entry point."""

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.finetuned import get_finetuned_model
from app.core.runtime_flags import is_safe_mode_enabled
from app.db.manager import get_connection_manager
from app.routers import auth, connection, export, nlq, schemas, visual, account
from app.routers import settings as settings_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup
    logger.info("Starting NL2SQL Agent application...")
    logger.info(f"LLM provider: {settings.llm_provider}")
    if settings.llm_provider.lower() == "ollama":
        logger.info(f"Ollama base URL: {settings.ollama_base_url}")
        logger.info(f"Default model: {settings.default_ollama_model}")
    elif settings.llm_provider.lower() in ("openrouter", "openai"):
        logger.info(f"LLM base URL: {settings.openrouter_base_url if settings.llm_provider.lower() == 'openrouter' else settings.openai_base_url}")
        logger.info(f"Default model: {settings.openrouter_model if settings.llm_provider.lower() == 'openrouter' else settings.openai_model}")
    logger.info(f"Safe mode: {is_safe_mode_enabled()}")
    finetuned = get_finetuned_model()
    if finetuned is None:
        logger.info("Post-trained text-to-SQL model not available (adapter or torch/transformers/peft missing)")
    else:
        logger.info(f"Post-trained text-to-SQL model available: {finetuned.name}")
        if settings.finetuned_preload:
            # Load in the background so the first query doesn't wait for it; startup isn't blocked.
            threading.Thread(target=finetuned.load, name="finetuned-preload", daemon=True).start()
    yield
    # Shutdown
    logger.info("Shutting down application...")
    # Cleanup connections
    manager = get_connection_manager()
    manager.cleanup_expired()


# Create FastAPI app
app = FastAPI(
    title="NL2SQL Agent",
    description="FastAPI + Ollama Natural Language to SQL Agent",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions globally."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {"error": str(exc)},
            }
        },
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


# Include routers
app.include_router(auth.router)  # Authentication endpoints (public)
app.include_router(connection.router)
app.include_router(schemas.router)
app.include_router(nlq.router)
app.include_router(visual.router)
app.include_router(export.router)
app.include_router(settings_router.router)
app.include_router(account.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )

