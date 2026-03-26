from dataclasses import dataclass

from dataclasses_json import dataclass_json

from models.scenario import CareersPageScenario, JobPageScenario


@dataclass_json
@dataclass
class Company:
    company: str
    url: str
    careers_page: CareersPageScenario
    job_page: JobPageScenario
    rps: float | None = None
