import json
from pathlib import Path

from scraper.models.job import Job
from scraper.models.scenario import CareersPageScenario, JobPageScenario
from scraper.storage.base import SiteConfig, Storage


class JsonStorage(Storage):
    def __init__(self, sites_dir: str, output_path: str):
        self.sites_dir = sites_dir
        self.output_path = output_path

    def load_site_configs(self) -> list[SiteConfig]:
        configs = []
        dir_path = Path(self.sites_dir)
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

    def save_jobs(self, jobs: list[Job]) -> None:
        output = [
            {
                "company": job.company,
                "title": job.title,
                "location": job.location,
                "description": job.description,
            }
            for job in jobs
        ]
        Path(self.output_path).write_text(json.dumps(output, indent=2))
