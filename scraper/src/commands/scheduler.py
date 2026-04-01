import logging

from pydantic_settings import BaseSettings

from dynamodb_storage import DynamoDbStorage
from models.config import DynamoDbConfig, SqsConfig
from sqs_queue import SqsQueue


class SchedulerConfig(BaseSettings):
    model_config = {"env_prefix": "SCRAPER_"}

    dynamodb: DynamoDbConfig = DynamoDbConfig()
    sqs: SqsConfig = SqsConfig()


logger = logging.getLogger(__name__)


async def run(storage: DynamoDbStorage, queue: SqsQueue):
    companies = await storage.load_companies()
    logger.info("Loaded %d companies from storage", len(companies))
    for company in companies:
        await queue.send_message(company)
        logger.info("Sent %s to queue", company.company)
    logger.info("Scheduler finished")


async def run_scheduler(config: SchedulerConfig):
    async with (
        DynamoDbStorage(config.dynamodb) as storage,
        SqsQueue(config.sqs) as queue,
    ):
        await run(storage, queue)
