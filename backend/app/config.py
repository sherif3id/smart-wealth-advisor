from functools import lru_cache
from pydantic import model_validator
from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
    app_env:str="development"
    database_url:str
    jwt_secret:str="development-only-change-me"
    jwt_algorithm:str="HS256"
    jwt_issuer:str="smart-wealth-core"
    jwt_audience:str="smart-wealth-bff"
    access_token_minutes:int=30
    cors_origins:str="http://localhost:3000"
    ml_service_url:str="http://localhost:8001"
    request_timeout_seconds:float=8.0
    auto_create_tables:bool=False
    trust_proxy_headers:bool=False
    smtp_host:str|None=None
    smtp_port:int=465
    smtp_user:str|None=None
    smtp_pass:str|None=None
    notification_from:str="Smart Wealth Advisor <no-reply@example.com>"
    cron_secret:str|None=None
    model_config=SettingsConfigDict(env_file=(".env","../.env"),extra="ignore")

    @model_validator(mode="after")
    def production_safety(self):
        if self.app_env.lower()=="production":
            if not self.database_url.startswith(("postgresql://","postgresql+psycopg://")):raise ValueError("Production DATABASE_URL must use PostgreSQL")
            if len(self.jwt_secret)<32 or self.jwt_secret=="development-only-change-me":raise ValueError("Production JWT_SECRET must be at least 32 non-default characters")
            if self.auto_create_tables:raise ValueError("AUTO_CREATE_TABLES is forbidden in production; use Alembic")
        return self

    @property
    def origins(self)->list[str]:return [value.strip() for value in self.cors_origins.split(",") if value.strip()]

@lru_cache
def get_settings()->Settings:return Settings()
