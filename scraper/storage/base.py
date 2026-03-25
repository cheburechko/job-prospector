from abc import ABC, abstractmethod

from models.company import Company
from models.job import Job


class Storage(ABC):
    @abstractmethod
    def load_companies(self) -> list[Company]: ...

    @abstractmethod
    def add_company(self, company: Company) -> None: ...

    @abstractmethod
    def delete_company(self, company: str) -> None: ...

    @abstractmethod
    def add_job(self, jobs: Job) -> None: ...

    @abstractmethod
    def delete_job(self, company: str, url: str) -> None: ...

    @abstractmethod
    def list_jobs(self, company: str) -> list[Job]: ...
