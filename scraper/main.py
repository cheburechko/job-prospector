import asyncio
import sys
from playwright.async_api import async_playwright

from config import ScraperConfig, load_config
from rate_limiter import RateLimiter
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

        async def scrape_one(site):
            limiter = RateLimiter(rps=site.rps if site.rps is not None else config.rps)
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

    storage.save_jobs(all_jobs)


def main():
    config = load_config()
    storage = JsonStorage(
        sites_dir=config.sites_dir,
        output_path=config.output_path,
    )
    asyncio.run(run(storage, config))


if __name__ == "__main__":
    main()
