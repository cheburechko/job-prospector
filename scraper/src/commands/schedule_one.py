import logging

from pydantic_settings import BaseSettings

from dynamodb_storage import DynamoDbStorage
from models.config import DynamoDbConfig, SqsConfig
from sqs_queue import SqsQueue

logger = logging.getLogger(__name__)


class ScheduleOne(BaseSettings):
    model_config = {"env_prefix": "SCRAPER_"}

    company: str
    dynamodb: DynamoDbConfig = DynamoDbConfig()
    sqs: SqsConfig = SqsConfig()

    async def cli_cmd(self) -> None:
        async with DynamoDbStorage(self.dynamodb) as storage:
            company = await storage.get_company(self.company)

        if company is None:
            raise ValueError(f"Company '{self.company}' not found in DynamoDB")

        async with SqsQueue(self.sqs) as queue:
            await queue.send_message(company)

        logger.info("Scheduled %s for processing", company.company)
