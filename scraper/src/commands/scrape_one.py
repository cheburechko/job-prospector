import json
import logging

from pydantic_settings import BaseSettings

from template.scraper import Scraper
from dynamodb_storage import DynamoDbStorage
from models.company import Company
from models.config import DynamoDbConfig, ProxyConfig, ScraperConfig

logger = logging.getLogger(__name__)


class ScrapeOne(BaseSettings):
    model_config = {"env_prefix": "SCRAPER_"}

    input: str | None = None
    company: str | None = None
    output: str = "out.json"
    proxy: ProxyConfig = ProxyConfig()
    dynamodb: DynamoDbConfig = DynamoDbConfig()
    scraper: ScraperConfig = ScraperConfig()
    limit: int | None = None

    async def cli_cmd(self) -> None:
        if self.input:
            with open(self.input) as f:
                company = Company.from_dict(json.load(f))
        elif self.company:
            async with DynamoDbStorage(self.dynamodb) as storage:
                company = await storage.get_company(self.company)
            if company is None:
                raise ValueError(f"Company '{self.company}' not found in DynamoDB")
        else:
            raise ValueError("Either --input or --company must be provided")

        async with Scraper(self.proxy, self.scraper) as scraper:
            result = await scraper.scrape(company, self.limit)

        result = [job.to_dict() for job in result.jobs]
        with open(self.output, "w") as f:
            json.dump(result, f, indent=2)

        logger.info("Scraped %d jobs, written to %s", len(result), self.output)
