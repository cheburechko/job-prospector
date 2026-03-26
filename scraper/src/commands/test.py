import json
import logging

from template.scraper import Scraper
from models.company import Company
from models.config import TestConfig

logger = logging.getLogger(__name__)


async def run_test(config: TestConfig):
    with open(config.input) as f:
        company = Company.from_dict(json.load(f))

    async with Scraper(config.proxy, config.scraper) as scraper:
        jobs = await scraper.scrape(company)

    result = [job.to_dict() for job in jobs]
    with open(config.output, "w") as f:
        json.dump(result, f, indent=2)

    logger.info("Scraped %d jobs, written to %s", len(jobs), config.output)
