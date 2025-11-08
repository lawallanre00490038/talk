# app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, AnyHttpUrl, ConfigDict
from typing import List, Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "LagTALK API"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours
    
    # Database
    DATABASE_URL: PostgresDsn
    DATABASE_URL_ASYNC: str = None

    FRONTEND_URL: str

    RESEND_API_KEY: Optional[str] = None
    RESEND_FROM_EMAIL: Optional[str] = "noreply@genaigov.ai"
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = ["*"]

    # S3 Media Storage
    S3_ENDPOINT_URL: str
    S3_ACCESS_KEY_ID: str
    S3_SECRET_ACCESS_KEY: str
    S3_BUCKET_NAME: str
    S3_PRESIGNED_URL_EXPIRATION: int = 3600 # 1 hour

    # Rate Limiting
    REDIS_URL: str

    # Grafana (for docker-compose)
    GF_SECURITY_ADMIN_USER: str = "admin"
    GF_SECURITY_ADMIN_PASSWORD: str = "grafana"

    model_config = ConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="ignore"
    )

settings = Settings()