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
        known_urls = await storage.list_job_urls(msg.company.company)
        result = await scraper.scrape(msg.company, known_urls=known_urls)
        async with storage.job_writer() as writer:
            await asyncio.gather(
                *(writer.add(job) for job in result.jobs),
                *(
                    writer.delete(msg.company.company, url)
                    for url in result.deleted_urls
                ),
            )
        await queue.delete_message(msg.receipt_handle)
        logger.info(
            "Scraped %s: %d new, %d deleted",
            msg.company.company,
            len(result.jobs),
            len(result.deleted_urls),
        )
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
