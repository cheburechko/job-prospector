import collections
import itertools
from pathlib import Path

import aiofiles
import aiofiles.os

from models.company import Company
from models.config import JsonStorageConfig
from models.job import Job
from storage.base import Storage


class JsonStorage(Storage):
    def __init__(self, config: JsonStorageConfig):
        self.sites_dir = Path(config.sites_dir)
        self.output_path = Path(config.output_path)
        self.jobs = self._get_jobs()

    async def load_companies(self) -> list[Company]:
        companies = []
        for path in sorted(self.sites_dir.glob("*.json")):
            async with aiofiles.open(path) as f:
                companies.append(Company.from_json(await f.read()))
        return companies

    async def add_company(self, company: Company) -> None:
        path = self.sites_dir / f"{company.company}.json"
        async with aiofiles.open(path, "w") as f:
            await f.write(company.to_json(indent=2))

    async def delete_company(self, company: str) -> None:
        path = self.sites_dir / f"{company}.json"
        await aiofiles.os.remove(path)

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

    async def _save_jobs(self) -> None:
        jobs_iter = itertools.chain.from_iterable(
            x.values() for x in self.jobs.values()
        )
        content = Job.schema().dumps(jobs_iter, many=True, indent=2)
        async with aiofiles.open(self.output_path, "w") as f:
            await f.write(content)

    async def add_job(self, job: Job) -> None:
        self.jobs[job.company][job.url] = job
        await self._save_jobs()

    async def delete_job(self, company: str, url: str) -> None:
        del self.jobs[company][url]
        await self._save_jobs()

    async def list_jobs(self, company: str) -> list[Job]:
        return list(self.jobs[company].values())
