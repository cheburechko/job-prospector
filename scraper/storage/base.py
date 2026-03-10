from abc import ABC, abstractmethod

from scraper.config import SiteConfig
from scraper.models.job import Job


class Storage(ABC):
    @abstractmethod
    def load_site_configs(self) -> list[SiteConfig]: ...

    @abstractmethod
    def save_jobs(self, jobs: list[Job]) -> None: ...
