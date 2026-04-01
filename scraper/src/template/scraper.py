from playwright.async_api import async_playwright
from pyrate_limiter import Duration, InMemoryBucket, Limiter, Rate

from models.company import Company
from models.config import ProxyConfig, ScraperConfig
from template.engine import ScrapeResult
from template.engine import ScrapingEngine


class Scraper:
    def __init__(self, proxy: ProxyConfig, scraper: ScraperConfig):
        self.proxy = proxy
        self.rps = scraper.rps
        self.timeout = scraper.timeout

    async def __aenter__(self):
        self._pw = await async_playwright().start()

        launch_args = {}
        if self.proxy.enabled:
            launch_args["proxy"] = {
                "server": self.proxy.server,
                "username": self.proxy.username,
                "password": self.proxy.password,
            }

        self._browser = await self._pw.chromium.launch()
        self._context = await self._browser.new_context(**launch_args)
        self._context.set_default_timeout(self.timeout)
        return self

    async def __aexit__(self, *exc):
        await self._context.close()
        await self._browser.close()
        await self._pw.stop()

    async def scrape(
        self, site: Company, limit: int = None, known_urls: set[str] = None
    ) -> ScrapeResult:
        rps = site.rps if site.rps is not None else self.rps
        bucket = InMemoryBucket([Rate(int(rps), Duration.SECOND)])
        limiter = Limiter(bucket)
        engine = ScrapingEngine(self._context, limiter)
        return await engine.scrape_site(
            url=site.url,
            company=site.company,
            careers=site.careers_page,
            job_page=site.job_page,
            limit=limit,
            known_urls=known_urls,
        )
