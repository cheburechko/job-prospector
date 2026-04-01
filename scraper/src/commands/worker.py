import asyncio
import logging

from pydantic_settings import BaseSettings

from template.scraper import Scraper
from dynamodb_storage import DynamoDbStorage
from models.config import DynamoDbConfig, ProxyConfig, ScraperConfig, SqsConfig
from sqs_queue import QueueMessage, SqsQueue


class WorkerConfig(BaseSettings):
    model_config = {"env_prefix": "SCRAPER_"}

    proxy: ProxyConfig = ProxyConfig()
    dynamodb: DynamoDbConfig = DynamoDbConfig()
    sqs: SqsConfig = SqsConfig()
    scraper: ScraperConfig = ScraperConfig()
    max_concurrency: int = 5


logger = logging.getLogger(__name__)


async def process_message(
    msg: QueueMessage,
    scraper: Scraper,
    storage: DynamoDbStorage,
    queue: SqsQueue,
    semaphore: asyncio.Semaphore,
):
    try:
        logger.info("Scraping %s", msg.company.company)
        jobs = await scraper.scrape(msg.company)
        for job in jobs:
            await storage.add_job(job)
        await queue.delete_message(msg.receipt_handle)
        logger.info("Scraped %s: %d jobs", msg.company.company, len(jobs))
    finally:
        semaphore.release()


async def run(storage: DynamoDbStorage, queue: SqsQueue, config: WorkerConfig):
    semaphore = asyncio.Semaphore(config.max_concurrency)
    logger.info("Worker started, max_concurrency=%d", config.max_concurrency)

    async with Scraper(config.proxy, config.scraper) as scraper:
        async with asyncio.TaskGroup() as tg:
            while True:
                messages = await queue.receive_messages()
                if messages:
                    logger.info("Received %d messages", len(messages))
                for msg in messages:
                    await semaphore.acquire()
                    tg.create_task(
                        process_message(msg, scraper, storage, queue, semaphore)
                    )


async def run_worker(config: WorkerConfig):
    async with (
        DynamoDbStorage(config.dynamodb) as storage,
        SqsQueue(config.sqs) as queue,
    ):
        await run(storage, queue, config)
