import collections
import itertools
from pathlib import Path

from models.job import Job
from storage.base import SiteConfig, Storage


class JsonStorage(Storage):
    def __init__(self, sites_dir: str, output_path: str):
        self.sites_dir = Path(sites_dir)
        self.output_path = Path(output_path)
        self.jobs = self._get_jobs()

    def load_site_configs(self) -> list[SiteConfig]:
        configs = []
        for path in sorted(self.sites_dir.glob("*.json")):
            with open(path) as f:
                configs.append(SiteConfig.from_json(f.read()))
        return configs

    def add_site_config(self, site_config: SiteConfig) -> None:
        path = self.sites_dir / f"{site_config.company}.json"
        path.write_text(site_config.to_json(indent=2))

    def delete_site_config(self, company: str) -> None:
        path = self.sites_dir / f"{company}.json"
        path.unlink()

    def _get_jobs(self) -> dict[str, dict[str, Job]]:
        result = collections.defaultdict(dict)
        if not self.output_path.exists():
            return result
        with open(self.output_path) as f:
            for job in Job.schema().load(
                f,
                many=True,
            ):
                result[job.company][job.url] = job
        return result

    def _save_jobs(self) -> None:
        jobs_iter = itertools.chain.from_iterable(
            x.values() for x in self.jobs.values()
        )
        self.output_path.write_text(Job.schema().dumps(jobs_iter, many=True, indent=2))

    def add_job(self, job: Job) -> None:
        self.jobs[job.company][job.url] = job
        self._save_jobs()

    def delete_job(self, company: str, url: str) -> None:
        del self.jobs[company][url]
        self._save_jobs()

    def list_jobs(self, company: str) -> list[Job]:
        return list(self.jobs[company].values())
