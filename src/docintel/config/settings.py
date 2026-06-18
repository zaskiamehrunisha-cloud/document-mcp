"""
Application settings using Pydantic Settings.
All configuration is loaded from environment variables and config files.
"""

import os
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment and config files."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    app_name: str = Field(default="docintel", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    
    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------
    database_url: str = Field(
        default="postgresql+psycopg://docintel:docintel@localhost:5432/docintel",
        alias="DATABASE_URL",
    )
    
    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL is required")
        return v
    
    # -------------------------------------------------------------------------
    # LLM Configuration
    # -------------------------------------------------------------------------
    llm_base_url: str = Field(default="http://localhost:11434/v1", alias="LLM_BASE_URL")
    llm_api_key: str = Field(default="ollama", alias="LLM_API_KEY")
    llm_model: str = Field(default="llama3.2:3b-instruct-q4_K_M", alias="LLM_MODEL")
    llm_temperature: float = Field(default=0.1, alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=4096, alias="LLM_MAX_TOKENS")
    
    @field_validator("llm_temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if not 0.0 <= v <= 2.0:
            raise ValueError("LLM temperature must be between 0.0 and 2.0")
        return v
    
    # -------------------------------------------------------------------------
    # Embedding Configuration
    # -------------------------------------------------------------------------
    embedding_model: str = Field(default="BAAI/bge-large-en-v1.5", alias="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=1024, alias="EMBEDDING_DIMENSION")
    embedding_device: str = Field(default="cpu", alias="EMBEDDING_DEVICE")
    
    @field_validator("embedding_device")
    @classmethod
    def validate_embedding_device(cls, v: str) -> str:
        valid = {"cpu", "cuda", "mps"}
        if v.lower() not in valid:
            raise ValueError(f"Embedding device must be one of {valid}")
        return v.lower()
    
    # -------------------------------------------------------------------------
    # OCR Configuration
    # -------------------------------------------------------------------------
    ocr_engine: str = Field(default="paddle", alias="OCR_ENGINE")
    paddle_use_angle_cls: bool = Field(default=True, alias="PADDLE_USE_ANGLE_CLS")
    tesseract_cmd: str = Field(
        default="/usr/bin/tesseract",
        alias="TESSERACT_CMD",
    )
    ocr_lang: str = Field(default="en", alias="OCR_LANG")
    ocr_confidence_threshold: float = Field(default=0.7, alias="OCR_CONFIDENCE_THRESHOLD")
    
    @field_validator("ocr_engine")
    @classmethod
    def validate_ocr_engine(cls, v: str) -> str:
        valid = {"paddle", "tesseract"}
        if v.lower() not in valid:
            raise ValueError(f"OCR engine must be one of {valid}")
        return v.lower()
    
    # -------------------------------------------------------------------------
    # Validation Configuration
    # -------------------------------------------------------------------------
    validation_confidence_threshold: float = Field(
        default=0.6, alias="VALIDATION_CONFIDENCE_THRESHOLD"
    )
    document_number_regex: str = Field(
        default=r"^[A-Z]{3}-[A-Z]-[A-Z]{2}-\d{2}-\d{3}$",
        alias="DOCUMENT_NUMBER_REGEX",
    )
    contract_number: str = Field(default="3500003752", alias="CONTRACT_NUMBER")
    
    # -------------------------------------------------------------------------
    # DOCON Configuration
    # -------------------------------------------------------------------------
    docon_mode: str = Field(default="mock", alias="DOCON_MODE")
    docon_api_url: str = Field(default="http://localhost:8080/docon", alias="DOCON_API_URL")
    docon_api_key: str = Field(default="", alias="DOCON_API_KEY")
    docon_drop_path: str = Field(default="/var/docon/inbox", alias="DOCON_DROP_PATH")
    
    @field_validator("docon_mode")
    @classmethod
    def validate_docon_mode(cls, v: str) -> str:
        valid = {"mock", "rest", "file_drop"}
        if v.lower() not in valid:
            raise ValueError(f"DOCON mode must be one of {valid}")
        return v.lower()
    
    # -------------------------------------------------------------------------
    # Offline Guard Configuration
    # -------------------------------------------------------------------------
    allowed_hosts: str = Field(
        default="localhost,127.0.0.1,::1,ollama,vllm,localhost.localdomain",
        alias="ALLOWED_HOSTS",
    )
    
    @property
    def allowed_hosts_list(self) -> List[str]:
        """Parse the comma-separated allowed hosts into a list."""
        return [h.strip() for h in self.allowed_hosts.split(",") if h.strip()]
    
    # -------------------------------------------------------------------------
    # CORS Configuration
    # -------------------------------------------------------------------------
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        alias="CORS_ORIGINS",
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse the comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
    
    # -------------------------------------------------------------------------
    # Paths
    # -------------------------------------------------------------------------
    reference_data_path: str = Field(default="./data/reference", alias="REFERENCE_DATA_PATH")
    upload_temp_path: str = Field(default="./tmp/uploads", alias="UPLOAD_TEMP_PATH")
    chunk_size: int = Field(default=512, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, alias="CHUNK_OVERLAP")
    
    # -------------------------------------------------------------------------
    # Computed Properties
    # -------------------------------------------------------------------------
    
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"
    
    @property
    def is_development(self) -> bool:
        return self.app_env == "development"
    
    @property
    def reference_data_dir(self) -> Path:
        return Path(self.reference_data_path)
    
    @property
    def upload_temp_dir(self) -> Path:
        return Path(self.upload_temp_path)


# Global settings instance
settings = Settings()