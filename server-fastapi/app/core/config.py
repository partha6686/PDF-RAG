from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Server Configuration
    PORT: int = 8000
    DEBUG: bool = True
    
    # Database Configuration
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/pdf_rag"
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Qdrant Configuration
    QDRANT_URL: str = "http://localhost:6333"
    
    # MinIO S3 Storage Configuration
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    
    # Google Gemini API
    GOOGLE_API_KEY: str
    
    # JWT Authentication
    JWT_SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 30
    
    # Processing Configuration
    CHUNK_SIZE: int = 2000
    CHUNK_OVERLAP: int = 400
    MAX_FILE_SIZE_MB: int = 50
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()