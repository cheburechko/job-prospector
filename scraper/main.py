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

    rate_limiter = RateLimiter(rps=config.rps)

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
        engine = ScrapingEngine(context, rate_limiter)

        all_jobs = []
        for site in site_configs:
            jobs = await engine.scrape_site(
                url=site.url,
                company=site.company,
                careers=site.careers_page,
                job_page=site.job_page,
            )
            all_jobs.extend(jobs)

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
