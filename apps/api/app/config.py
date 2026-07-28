from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Perinatal Contacts API"
    database_url: str = "sqlite+pysqlite:////tmp/pnc.db"
    admin_api_key: str = "dev-admin-key-change-me"
    public_api_key: str = ""
    storage_dir: str = "storage"
    seed_csv_path: str = "data/seed/institutions.csv"
    crawl_allowlist: str = "ncagp.ru,example.com,localhost"
    allow_live_mail: bool = False
    cors_origins: str = "*"


@lru_cache
def get_settings() -> Settings:
    return Settings()
