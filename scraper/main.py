import asyncio
import sys
from playwright.async_api import async_playwright

from config import ScraperConfig, load_config, StorageType
from pyrate_limiter import Duration, Rate, InMemoryBucket, Limiter
from storage.base import Storage
from storage.json_storage import JsonStorage
from template.engine import ScrapingEngine


async def run(storage: Storage, config: ScraperConfig):
    site_configs = storage.load_site_configs()

    if not site_configs:
        print("No site configs found", file=sys.stderr)
        return

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

        results = await asyncio.gather(*(scrape_one(site) for site in site_configs))
        all_jobs = [job for jobs in results for job in jobs]

        await context.close()
        await browser.close()

    for job in all_jobs:
        storage.add_job(job)


def main():
    config = load_config()
    if config.storage_type == StorageType.DYNAMODB:
        from storage.dynamodb_storage import DynamoDbStorage

        storage = DynamoDbStorage(
            configs_table=config.dynamodb.configs_table,
            jobs_table=config.dynamodb.jobs_table,
            region=config.dynamodb.region,
            endpoint_url=config.dynamodb.endpoint_url,
        )
    else:
        storage = JsonStorage(
            sites_dir=config.sites_dir,
            output_path=config.output_path,
        )
    asyncio.run(run(storage, config))


if __name__ == "__main__":
    main()
