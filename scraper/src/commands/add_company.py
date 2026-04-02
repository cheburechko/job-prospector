import json
import logging

from pydantic_settings import BaseSettings

from dynamodb_storage import DynamoDbStorage
from models.company import Company
from models.config import DynamoDbConfig

logger = logging.getLogger(__name__)


class AddCompany(BaseSettings):
    model_config = {"env_prefix": "SCRAPER_"}

    input: str
    dynamodb: DynamoDbConfig = DynamoDbConfig()

    async def cli_cmd(self) -> None:
        with open(self.input) as f:
            company = Company.from_dict(json.load(f))

        async with DynamoDbStorage(self.dynamodb) as storage:
            async with storage.company_writer() as writer:
                await writer.add(company)

        logger.info("Added company %s", company.company)
