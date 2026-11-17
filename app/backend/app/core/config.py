"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root: app/backend/app/core/config.py -> four levels up.
_REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")

    # CORS
    allowed_origins: str = Field(default="*", alias="ALLOWED_ORIGINS")

    # Ollama
    default_ollama_model: str = Field(default="llama3.1", alias="DEFAULT_OLLAMA_MODEL")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")

    # LLM provider selection: ollama | openai | hf
    llm_provider: str = Field(default="ollama", alias="LLM_PROVIDER")

    # OpenAI / compatible APIs
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com", alias="OPENAI_BASE_URL")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    # OpenRouter (OpenAI-compatible)
    openrouter_api_key: Optional[str] = Field(default=None, alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL")
    openrouter_model: str = Field(default="openrouter/llama-3.1-8b-instruct", alias="OPENROUTER_MODEL")

    # Hugging Face Inference (text generation)
    hf_api_key: Optional[str] = Field(default=None, alias="HF_API_KEY")
    hf_base_url: str = Field(default="https://api-inference.huggingface.co", alias="HF_BASE_URL")
    hf_model: str = Field(default="meta-llama/Llama-3-8b-Instruct", alias="HF_MODEL")

    # Post-trained text-to-SQL model (Qwen2.5-Coder-0.5B + SFT/DPO LoRA), run in-process.
    finetuned_enabled: bool = Field(default=True, alias="FINETUNED_ENABLED")
    finetuned_model_name: str = Field(default="text2sql-qwen-0.5b-dpo", alias="FINETUNED_MODEL_NAME")
    finetuned_base_model: str = Field(
        default="Qwen/Qwen2.5-Coder-0.5B-Instruct", alias="FINETUNED_BASE_MODEL"
    )
    finetuned_adapter_path: str = Field(
        default=str(_REPO_ROOT / "models" / "text2sql-qwen-dpo"), alias="FINETUNED_ADAPTER_PATH"
    )
    finetuned_max_new_tokens: int = Field(default=256, alias="FINETUNED_MAX_NEW_TOKENS")
    finetuned_preload: bool = Field(default=True, alias="FINETUNED_PRELOAD")

    # Security
    execution_safe_mode: bool = Field(default=True, alias="EXECUTION_SAFE_MODE")
    query_row_limit: int = Field(default=1000, alias="QUERY_ROW_LIMIT")
    query_timeout_seconds: int = Field(default=30, alias="QUERY_TIMEOUT_SECONDS")

    # MongoDB
    mongo_uri: str = Field(default="mongodb://localhost:27017", alias="MONGO_URI")
    mongo_db_name: str = Field(default="nl2sql_agent", alias="MONGO_DB_NAME")

    # Connection cache
    connection_expiry_minutes: int = Field(default=60, alias="CONNECTION_EXPIRY_MINUTES")

    # Authentication
    jwt_secret_key: Optional[str] = Field(default=None, alias="JWT_SECRET_KEY")
    jwt_access_token_expire_minutes: int = Field(default=60 * 24, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(default=7, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS")

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse ALLOWED_ORIGINS into a list."""
        if self.allowed_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

