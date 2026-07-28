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
    sites_registry_path: str = "data/registry/official_sites.yaml"
    crawl_allowlist: str = (
        "ncagp.ru,opc33.ru,perinatal-rostov.ru,pncenter.ru,perinatal-komi.ru,"
        "example.com,localhost,openstreetmap.org,nominatim.openstreetmap.org,"
        "catalog.api.2gis.com,2gis.ru,search-maps.yandex.ru,yandex.ru,"
        "orgpage.ru,www.orgpage.ru,medadvisor.ru,www.kp.ru,kp.ru,zdrav.expert,"
        "russiamedtravel.ru,vademec.ru,minzdrav.gov-murman.ru"
    )
    crawl_delay_sec: float = 1.0
    dgis_api_key: str = ""
    yandex_maps_api_key: str = ""
    allow_live_mail: bool = False
    cors_origins: str = "*"


@lru_cache
def get_settings() -> Settings:
    return Settings()
