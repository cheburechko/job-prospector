import json
import os
from dataclasses import dataclass
from pathlib import Path

from scraper.models.scenario import CareersPageScenario, JobPageScenario


@dataclass
class ProxyConfig:
    enabled: bool
    server: str = ""
    username: str = ""
    password: str = ""


@dataclass
class SiteConfig:
    company: str
    url: str
    careers_page: CareersPageScenario
    job_page: JobPageScenario
    rps: float | None = None


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


def load_site_configs(directory: str) -> list[SiteConfig]:
    configs = []
    dir_path = Path(directory)
    for path in sorted(dir_path.glob("*.json")):
        with open(path) as f:
            data = json.load(f)
        configs.append(
            SiteConfig(
                company=data["company"],
                url=data["url"],
                careers_page=CareersPageScenario.from_dict(data["careers_page"]),
                job_page=JobPageScenario.from_dict(data["job_page"]),
                rps=data.get("rps"),
            )
        )
    return configs
