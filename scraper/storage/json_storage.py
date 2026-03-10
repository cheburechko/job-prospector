from pathlib import Path

from scraper.models.job import Job
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
                configs.append(SiteConfig.from_json(f.read()))
        return configs

    def save_jobs(self, jobs: list[Job]) -> None:
        Path(self.output_path).write_text(Job.schema().dumps(jobs, indent=2, many=True))
