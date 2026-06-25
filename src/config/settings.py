"""Application settings using pydantic-settings."""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Database Configuration
    db_url: str = "postgresql+asyncpg://doccontrol:secure_password@localhost:5432/engineering_docs"
    db_echo: bool = False
    
    # Ollama Configuration (Local LLM)
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b-instruct-q4_K_M"
    ollama_fallback_model: str = "qwen2.5:7b-instruct-q4_K_M"
    
    # Embedding Model
    embed_model: str = "BAAI/bge-small-en-v1.5"
    embed_cache_size: int = 1000
    
    # Document Controller Integration
    docon_api_url: str = "http://document-controller.internal:8080/api/v1/submissions"
    docon_api_key: str = ""
    docon_timeout: int = 30
    
    # Web UI Configuration
    start_web_ui: bool = True
    web_port: int = 8000
    web_host: str = "0.0.0.0"
    
    # Celery Configuration
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    
    # OCR Configuration
    ocr_dpi: int = 300
    ocr_confidence_threshold: float = 0.75
    ocr_lang: str = "en"
    ocr_use_gpu: bool = True
    ocr_fallback_dpi: int = 150
    
    # Chunking Configuration
    parent_chunk_size: int = 1024
    parent_chunk_overlap: int = 128
    child_chunk_size: int = 256
    child_chunk_overlap: int = 32
    
    # Validation Configuration
    validation_rule_reload_interval: int = 300
    
    # Security
    secret_key: str = "change_me_in_production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Admin Credentials
    admin_username: str = "admin"
    admin_password_hash: str = ""
    
    # File Storage
    upload_dir: str = "./data/uploads"
    preview_dir: str = "./data/previews"
    max_upload_size_mb: int = 100
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    @property
    def max_upload_size_bytes(self) -> int:
        """Convert MB to bytes."""
        return self.max_upload_size_mb * 1024 * 1024


# Global settings instance
settings = Settings()