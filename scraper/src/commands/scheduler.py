import logging

from pydantic_settings import BaseSettings

from dynamodb_storage import DynamoDbStorage
from models.config import DynamoDbConfig, SqsConfig
from sqs_queue import SqsQueue

logger = logging.getLogger(__name__)


class Scheduler(BaseSettings):
    model_config = {"env_prefix": "SCRAPER_"}

    dynamodb: DynamoDbConfig = DynamoDbConfig()
    sqs: SqsConfig = SqsConfig()

    async def cli_cmd(self) -> None:
        async with (
            DynamoDbStorage(self.dynamodb) as storage,
            SqsQueue(self.sqs) as queue,
        ):
            await run(storage, queue)


async def run(storage: DynamoDbStorage, queue: SqsQueue):
    companies = await storage.load_companies()
    logger.info("Loaded %d companies from storage", len(companies))
    for company in companies:
        await queue.send_message(company)
        logger.info("Sent %s to queue", company.company)
    logger.info("Scheduler finished")
