import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProxyConfig:
    enabled: bool
    server: str = ""
    username: str = ""
    password: str = ""


@dataclass
class ScraperConfig:
    proxy: ProxyConfig
    rps: float


def load_config() -> ScraperConfig:
    server = os.environ.get("PROXY_SERVER", "")
    username = os.environ.get("PROXY_USER", "")
    password = os.environ.get("PROXY_PASSWORD", "")

    if not password:
        secrets_path = Path(".secrets/proxy_password")
        if secrets_path.exists():
            password = secrets_path.read_text().strip()

    enabled = bool(server)
    proxy = ProxyConfig(
        enabled=enabled,
        server=server,
        username=username,
        password=password,
    )

    rps = float(os.environ.get("SCRAPER_RPS", "2.0"))

    return ScraperConfig(proxy=proxy, rps=rps)
