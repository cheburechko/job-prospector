import asyncio
import logging

from playwright.async_api import BrowserContext, async_playwright

from dynamodb_storage import DynamoDbStorage
from models.config import ScraperConfig
from pyrate_limiter import Duration, Rate, InMemoryBucket, Limiter
from sqs_queue import QueueMessage, SqsQueue
from template.engine import ScrapingEngine

logger = logging.getLogger(__name__)


def _make_limiter(rps: float) -> Limiter:
    bucket = InMemoryBucket([Rate(int(rps), Duration.SECOND)])
    return Limiter(bucket)


async def scrape_one(context: BrowserContext, site, default_rps: float):
    limiter = _make_limiter(site.rps if site.rps is not None else default_rps)
    engine = ScrapingEngine(context, limiter)
    return await engine.scrape_site(
        url=site.url,
        company=site.company,
        careers=site.careers_page,
        job_page=site.job_page,
    )


async def process_message(
    msg: QueueMessage,
    context: BrowserContext,
    storage: DynamoDbStorage,
    queue: SqsQueue,
    semaphore: asyncio.Semaphore,
    default_rps: float,
):
    try:
        logger.info("Scraping %s", msg.company.company)
        jobs = await scrape_one(context, msg.company, default_rps)
        for job in jobs:
            await storage.add_job(job)
        await queue.delete_message(msg.receipt_handle)
        logger.info("Scraped %s: %d jobs", msg.company.company, len(jobs))
    finally:
        semaphore.release()


async def run(storage: DynamoDbStorage, queue: SqsQueue, config: ScraperConfig):
    semaphore = asyncio.Semaphore(config.max_concurrency)
    logger.info("Worker started, max_concurrency=%d", config.max_concurrency)

    async with async_playwright() as p:
        launch_args = {}
        if config.proxy.enabled:
            launch_args["proxy"] = {
                "server": config.proxy.server,
                "username": config.proxy.username,
                "password": config.proxy.password,
            }

        browser = await p.chromium.launch()
        context = await browser.new_context(**launch_args)
        context.set_default_timeout(config.timeout)

        try:
            async with asyncio.TaskGroup() as tg:
                while True:
                    messages = await queue.receive_messages()
                    if messages:
                        logger.info("Received %d messages", len(messages))
                    for msg in messages:
                        await semaphore.acquire()
                        tg.create_task(
                            process_message(
                                msg, context, storage, queue, semaphore, config.rps
                            )
                        )
        finally:
            await context.close()
            await browser.close()


async def run_worker(config: ScraperConfig):
    async with (
        DynamoDbStorage(config.dynamodb) as storage,
        SqsQueue(config.sqs) as queue,
    ):
        await run(storage, queue, config)
