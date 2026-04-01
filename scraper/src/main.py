import logging

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_settings import CliApp, CliSubCommand

from commands.add_company import AddCompanyConfig, run_add_company
from commands.schedule_one import ScheduleOneConfig, run_schedule_one
from commands.scheduler import SchedulerConfig, run_scheduler
from commands.scrape_one import ScrapeOneConfig, run_scrape_one
from commands.worker import WorkerConfig, run_worker


class Worker(WorkerConfig):
    async def cli_cmd(self) -> None:
        await run_worker(self)


class Scheduler(SchedulerConfig):
    async def cli_cmd(self) -> None:
        await run_scheduler(self)


class ScrapeOne(ScrapeOneConfig):
    async def cli_cmd(self) -> None:
        await run_scrape_one(self)


class AddCompany(AddCompanyConfig):
    async def cli_cmd(self) -> None:
        await run_add_company(self)


class ScheduleOne(ScheduleOneConfig):
    async def cli_cmd(self) -> None:
        await run_schedule_one(self)


class Cli(BaseModel):
    worker: CliSubCommand[Worker]
    scheduler: CliSubCommand[Scheduler]
    scrape_one: CliSubCommand[ScrapeOne]
    add_company: CliSubCommand[AddCompany]
    schedule_one: CliSubCommand[ScheduleOne]

    def cli_cmd(self) -> None:
        CliApp.run_subcommand(self)


def main():
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    CliApp.run(Cli)


if __name__ == "__main__":
    main()
