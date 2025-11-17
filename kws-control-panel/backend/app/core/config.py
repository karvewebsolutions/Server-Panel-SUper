from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="KWS Control Panel API")
    environment: str = Field(default="development")
    secret_key: str = Field(default="changeme")
    access_token_expire_minutes: int = Field(default=60 * 24)
    database_url: str = Field(default="postgresql://kws:kws@postgres:5432/kws")
    redis_url: str = Field(default="redis://redis:6379/0")
    admin_email: str = Field(default="admin@karve.fun")
    admin_password: str = Field(default="admin123")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


class TokenConfig(BaseModel):
    token_type: str = "bearer"
    expires_in: int = 60 * 24


def get_settings() -> Settings:
    return Settings()


def get_token_config() -> TokenConfig:
    return TokenConfig(expires_in=Settings().access_token_expire_minutes)
