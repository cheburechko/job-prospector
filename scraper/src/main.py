import asyncio
import logging

from pydantic import BaseModel
from pydantic_settings import CliApp, CliSubCommand

from commands.scheduler import SchedulerConfig, run_scheduler
from commands.test import TestConfig, run_test
from commands.worker import WorkerConfig, run_worker


class Worker(WorkerConfig):
    def cli_cmd(self) -> None:
        asyncio.run(run_worker(self))


class Scheduler(SchedulerConfig):
    def cli_cmd(self) -> None:
        asyncio.run(run_scheduler(self))


class Test(TestConfig):
    def cli_cmd(self) -> None:
        asyncio.run(run_test(self))


class Cli(BaseModel):
    worker: CliSubCommand[Worker]
    scheduler: CliSubCommand[Scheduler]
    test: CliSubCommand[Test]

    def cli_cmd(self) -> None:
        CliApp.run_subcommand(self)


def main():
    logging.basicConfig(level=logging.INFO)
    CliApp.run(Cli)


if __name__ == "__main__":
    main()
