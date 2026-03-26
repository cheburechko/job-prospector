import asyncio
import logging

from pydantic import BaseModel
from pydantic_settings import CliApp, CliSubCommand

from commands.scheduler import run_scheduler
from commands.worker import run_worker
from models.config import ScraperConfig, SchedulerConfig


class Worker(ScraperConfig):
    def cli_cmd(self) -> None:
        asyncio.run(run_worker(self))


class Scheduler(SchedulerConfig):
    def cli_cmd(self) -> None:
        asyncio.run(run_scheduler(self))


class Cli(BaseModel):
    worker: CliSubCommand[Worker]
    scheduler: CliSubCommand[Scheduler]

    def cli_cmd(self) -> None:
        CliApp.run_subcommand(self)


def main():
    logging.basicConfig(level=logging.INFO)
    CliApp.run(Cli)


if __name__ == "__main__":
    main()
