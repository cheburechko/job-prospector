import json
import logging

from pydantic_settings import BaseSettings

from dynamodb_storage import DynamoDbStorage
from models.company import Company
from models.config import DynamoDbConfig


class AddCompanyConfig(BaseSettings):
    model_config = {"env_prefix": "SCRAPER_", "env_file": ".env"}

    input: str
    dynamodb: DynamoDbConfig = DynamoDbConfig()


logger = logging.getLogger(__name__)


async def run_add_company(config: AddCompanyConfig):
    with open(config.input) as f:
        company = Company.from_dict(json.load(f))

    async with DynamoDbStorage(config.dynamodb) as storage:
        async with storage.company_writer() as writer:
            await writer.add(company)

    logger.info("Added company %s", company.company)
