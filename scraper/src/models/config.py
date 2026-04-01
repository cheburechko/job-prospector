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


class SqsConfig(BaseSettings):
    model_config = {"env_prefix": "SQS_"}

    queue_url: str = ""
    region: str = "eu-central-1"
    endpoint_url: str | None = None
    wait_time_seconds: int = 20
    max_messages: int = 10


class ScraperConfig(BaseSettings):
    rps: float = 2.0
    timeout: int = 5000
    max_retries: int = 3
    retry_base_delay: float = 1.0
