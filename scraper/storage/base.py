from abc import ABC, abstractmethod
from dataclasses import dataclass

from dataclasses_json import dataclass_json

from models.job import Job
from models.scenario import CareersPageScenario, JobPageScenario


@dataclass_json
@dataclass
class SiteConfig:
    company: str
    url: str
    careers_page: CareersPageScenario
    job_page: JobPageScenario
    rps: float | None = None


class Storage(ABC):
    @abstractmethod
    def load_site_configs(self) -> list[SiteConfig]: ...

    @abstractmethod
    def add_site_config(self, site_config: SiteConfig) -> None: ...

    @abstractmethod
    def delete_site_config(self, company: str) -> None: ...

    @abstractmethod
    def add_job(self, jobs: Job) -> None: ...

    @abstractmethod
    def delete_job(self, company: str, url: str) -> None: ...

    @abstractmethod
    def list_jobs(self, company: str) -> list[Job]: ...
