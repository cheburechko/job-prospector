import logging

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_settings import CliApp, CliSubCommand

from commands.add_company import AddCompany
from commands.schedule_one import ScheduleOne
from commands.scheduler import Scheduler
from commands.scrape_one import ScrapeOne
from commands.worker import Worker


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
