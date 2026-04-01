import json
import logging

from pydantic_settings import BaseSettings

from template.scraper import Scraper
from models.company import Company
from models.config import ProxyConfig, ScraperConfig


class TestConfig(BaseSettings):
    __test__ = False

    model_config = {"env_prefix": "SCRAPER_"}

    input: str
    output: str = "out.json"
    proxy: ProxyConfig = ProxyConfig()
    scraper: ScraperConfig = ScraperConfig()
    limit: int | None = None


logger = logging.getLogger(__name__)


async def run_test(config: TestConfig):
    with open(config.input) as f:
        company = Company.from_dict(json.load(f))

    async with Scraper(config.proxy, config.scraper) as scraper:
        result = await scraper.scrape(company, config.limit)

    result = [job.to_dict() for job in result.jobs]
    with open(config.output, "w") as f:
        json.dump(result, f, indent=2)

    logger.info("Scraped %d jobs, written to %s", len(result), config.output)
