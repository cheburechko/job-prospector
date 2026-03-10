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


class ScraperConfig(BaseSettings):
    model_config = {"env_prefix": "SCRAPER_"}

    proxy: ProxyConfig = ProxyConfig()
    rps: float = 2.0


def load_config() -> ScraperConfig:
    return ScraperConfig()
