import asyncio

from playwright.async_api import BrowserContext, async_playwright

from models.config import ScraperConfig
from pyrate_limiter import Duration, Rate, InMemoryBucket, Limiter
from queues.base import Queue, QueueMessage
from queues.sqs_queue import SqsQueue
from storage.base import Storage
from storage.dynamodb_storage import DynamoDbStorage
from template.engine import ScrapingEngine


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
    storage: Storage,
    queue: Queue,
    semaphore: asyncio.Semaphore,
    default_rps: float,
):
    try:
        jobs = await scrape_one(context, msg.company, default_rps)
        for job in jobs:
            await storage.add_job(job)
        await queue.delete_message(msg.receipt_handle)
    finally:
        semaphore.release()


async def run(storage: Storage, queue: Queue, config: ScraperConfig):
    semaphore = asyncio.Semaphore(config.max_concurrency)

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


def load_config() -> ScraperConfig:
    return ScraperConfig()


async def async_main():
    config = load_config()
    async with (
        DynamoDbStorage(config.dynamodb) as storage,
        SqsQueue(config.sqs) as queue,
    ):
        await run(storage, queue, config)


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
