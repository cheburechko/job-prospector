import json
import logging

from pydantic_settings import BaseSettings

from template.scraper import Scraper
from dynamodb_storage import DynamoDbStorage
from models.company import Company
from models.config import DynamoDbConfig, ProxyConfig, ScraperConfig


class ScrapeOneConfig(BaseSettings):
    model_config = {"env_prefix": "SCRAPER_", "env_file": ".env"}

    input: str | None = None
    company: str | None = None
    output: str = "out.json"
    proxy: ProxyConfig = ProxyConfig()
    dynamodb: DynamoDbConfig = DynamoDbConfig()
    scraper: ScraperConfig = ScraperConfig()
    limit: int | None = None


logger = logging.getLogger(__name__)


async def run_scrape_one(config: ScrapeOneConfig):
    if config.input:
        with open(config.input) as f:
            company = Company.from_dict(json.load(f))
    elif config.company:
        async with DynamoDbStorage(config.dynamodb) as storage:
            company = await storage.get_company(config.company)
        if company is None:
            raise ValueError(f"Company '{config.company}' not found in DynamoDB")
    else:
        raise ValueError("Either --input or --company must be provided")

    async with Scraper(config.proxy, config.scraper) as scraper:
        result = await scraper.scrape(company, config.limit)

    result = [job.to_dict() for job in result.jobs]
    with open(config.output, "w") as f:
        json.dump(result, f, indent=2)

    logger.info("Scraped %d jobs, written to %s", len(result), config.output)
