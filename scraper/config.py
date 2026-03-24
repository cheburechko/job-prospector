from enum import StrEnum

from pydantic import AliasChoices, Field, computed_field
from pydantic_settings import BaseSettings


class ProxyConfig(BaseSettings):
    model_config = {"env_prefix": "PROXY_"}

    server: str = ""
    username: str = Field(
        default="",
        validation_alias=AliasChoices("username", "PROXY_USER", "PROXY_USERNAME"),
    )
    password: str = ""

    @computed_field
    @property
    def enabled(self) -> bool:
        return bool(self.server)


class DynamoDbConfig(BaseSettings):
    model_config = {"env_prefix": "DYNAMODB_"}

    configs_table: str = "scraper-site-configs"
    jobs_table: str = "scraper-jobs"
    region: str = "eu-central-1"
    endpoint_url: str | None = None


class StorageType(StrEnum):
    JSON = "json"
    DYNAMODB = "dynamodb"


class ScraperConfig(BaseSettings):
    model_config = {"env_prefix": "SCRAPER_"}

    proxy: ProxyConfig = ProxyConfig()
    dynamodb: DynamoDbConfig = DynamoDbConfig()
    storage_type: StorageType = StorageType.JSON
    rps: float = 2.0
    timeout: int = 5000
    sites_dir: str = "/data/sites"
    output_path: str = "/data/output.json"


def load_config() -> ScraperConfig:
    return ScraperConfig()
