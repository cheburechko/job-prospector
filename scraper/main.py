import asyncio
from playwright.async_api import async_playwright

from models.config import ScraperConfig, StorageType
from pyrate_limiter import Duration, Rate, InMemoryBucket, Limiter
from queues.base import Queue
from queues.sqs_queue import SqsQueue
from storage.base import Storage
from storage.json_storage import JsonStorage
from template.engine import ScrapingEngine


async def run(storage: Storage, queue: Queue, config: ScraperConfig):
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

        def _make_limiter(rps: float) -> Limiter:
            bucket = InMemoryBucket([Rate(int(rps), Duration.SECOND)])
            return Limiter(bucket)

        async def scrape_one(site):
            limiter = _make_limiter(site.rps if site.rps is not None else config.rps)
            engine = ScrapingEngine(context, limiter)
            return await engine.scrape_site(
                url=site.url,
                company=site.company,
                careers=site.careers_page,
                job_page=site.job_page,
            )

        try:
            while True:
                messages = await queue.receive_messages()
                if not messages:
                    continue

                companies = [msg.company for msg in messages]
                results = await asyncio.gather(
                    *(scrape_one(site) for site in companies)
                )

                for msg, jobs in zip(messages, results):
                    for job in jobs:
                        storage.add_job(job)
                    await queue.delete_message(msg.receipt_handle)
        finally:
            await context.close()
            await browser.close()


def load_config() -> ScraperConfig:
    return ScraperConfig()


def main():
    config = load_config()
    if config.storage_type == StorageType.DYNAMODB:
        from storage.dynamodb_storage import DynamoDbStorage

        storage = DynamoDbStorage(config.dynamodb)
    else:
        storage = JsonStorage(config.json_storage)

    queue = SqsQueue(config.sqs)

    asyncio.run(run(storage, queue, config))


if __name__ == "__main__":
    main()
