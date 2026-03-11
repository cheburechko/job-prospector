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
    def save_jobs(self, jobs: list[Job]) -> None: ...
