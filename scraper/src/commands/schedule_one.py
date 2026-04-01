import logging

from pydantic_settings import BaseSettings

from dynamodb_storage import DynamoDbStorage
from models.config import DynamoDbConfig, SqsConfig
from sqs_queue import SqsQueue


class ScheduleOneConfig(BaseSettings):
    model_config = {"env_prefix": "SCRAPER_"}

    company: str
    dynamodb: DynamoDbConfig = DynamoDbConfig()
    sqs: SqsConfig = SqsConfig()


logger = logging.getLogger(__name__)


async def run_schedule_one(config: ScheduleOneConfig):
    async with DynamoDbStorage(config.dynamodb) as storage:
        company = await storage.get_company(config.company)

    if company is None:
        raise ValueError(f"Company '{config.company}' not found in DynamoDB")

    async with SqsQueue(config.sqs) as queue:
        await queue.send_message(company)

    logger.info("Scheduled %s for processing", company.company)
