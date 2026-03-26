import asyncio

from pydantic import BaseModel
from pydantic_settings import CliApp, CliSubCommand

from commands.worker import run_worker
from models.config import ScraperConfig


class Worker(ScraperConfig):
    def cli_cmd(self) -> None:
        asyncio.run(run_worker(self))


class Cli(BaseModel):
    worker: CliSubCommand[Worker]

    def cli_cmd(self) -> None:
        CliApp.run_subcommand(self)


def main():
    CliApp.run(Cli)


if __name__ == "__main__":
    main()
