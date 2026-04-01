import asyncio
import logging

from pydantic import BaseModel
from pydantic_settings import CliApp, CliSubCommand

from commands.add_company import AddCompanyConfig, run_add_company
from commands.scheduler import SchedulerConfig, run_scheduler
from commands.scrape_one import ScrapeOneConfig, run_scrape_one
from commands.worker import WorkerConfig, run_worker


class Worker(WorkerConfig):
    def cli_cmd(self) -> None:
        asyncio.run(run_worker(self))


class Scheduler(SchedulerConfig):
    def cli_cmd(self) -> None:
        asyncio.run(run_scheduler(self))


class ScrapeOne(ScrapeOneConfig):
    def cli_cmd(self) -> None:
        asyncio.run(run_scrape_one(self))


class AddCompany(AddCompanyConfig):
    def cli_cmd(self) -> None:
        asyncio.run(run_add_company(self))


class Cli(BaseModel):
    worker: CliSubCommand[Worker]
    scheduler: CliSubCommand[Scheduler]
    scrape_one: CliSubCommand[ScrapeOne]
    add_company: CliSubCommand[AddCompany]

    def cli_cmd(self) -> None:
        CliApp.run_subcommand(self)


def main():
    logging.basicConfig(level=logging.INFO)
    CliApp.run(Cli)


if __name__ == "__main__":
    main()
