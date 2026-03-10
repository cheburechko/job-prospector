import json
from pathlib import Path

from scraper.config import SiteConfig, load_site_configs
from scraper.models.job import Job
from scraper.storage.base import Storage


class JsonStorage(Storage):
    def __init__(self, sites_dir: str, output_path: str):
        self.sites_dir = sites_dir
        self.output_path = output_path

    def load_site_configs(self) -> list[SiteConfig]:
        return load_site_configs(self.sites_dir)

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
