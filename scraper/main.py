import asyncio
import json
import sys
from pathlib import Path

from playwright.async_api import async_playwright

from scraper.config import load_config, load_site_configs
from scraper.rate_limiter import RateLimiter
from scraper.template.engine import ScrapingEngine


async def main():
    config = load_config()
    sites_dir = str(Path(__file__).parent / "sites")
    site_configs = load_site_configs(sites_dir)

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

    output = [
        {
            "company": job.company,
            "title": job.title,
            "location": job.location,
            "description": job.description,
        }
        for job in all_jobs
    ]
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
