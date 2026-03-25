from abc import ABC, abstractmethod

from models.company import Company
from models.job import Job


class Storage(ABC):
    @abstractmethod
    async def load_companies(self) -> list[Company]: ...

    @abstractmethod
    async def add_company(self, company: Company) -> None: ...

    @abstractmethod
    async def delete_company(self, company: str) -> None: ...

    @abstractmethod
    async def add_job(self, jobs: Job) -> None: ...

    @abstractmethod
    async def delete_job(self, company: str, url: str) -> None: ...

    @abstractmethod
    async def list_jobs(self, company: str) -> list[Job]: ...
