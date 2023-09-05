import secrets
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, BaseSettings, PostgresDsn, validator, SecretStr


class Settings(BaseSettings):
    DEV: bool = False
    RUN_TASKS: bool = True
    API_V1_STR: str = '/api/v1'
    SECRET_KEY: SecretStr = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 365

    # BACKEND_CORS_ORIGINS is a JSON-formatted list of origins
    # e.g: '["http://localhost", "http://localhost:4200", "http://localhost:3000", \
    # "http://localhost:8080", "http://local.dockertoolbox.tiangolo.com"]'
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    PROJECT_NAME: str = "ScraperBot"

    FIRST_CLIENT: Optional[str] = ''

    DATABASE_URL: PostgresDsn
    
    REDISHOST: str
    REDISPORT: int
    REDISPASSWORD: SecretStr

    TELEGRAM_BOT_API_KEY: SecretStr
    TELEGRAM_BOT_WEBHOOK_ENDPOINT: str
    TELEGRAM_BOT_WEBHOOK_SECRET: SecretStr
    
    YOUTUBE_API_KEY: SecretStr
    
    INTERVAL: int = 600

    SCRAPER_ATTEMPTS: int = 3
    SCRAPER_INTERVAL: float = 1.0

    class Config:
        case_sensitive = True


settings = Settings()
