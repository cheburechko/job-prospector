import logging
import urllib.parse
from dataclasses import dataclass, field

from playwright.async_api import BrowserContext
from tenacity import (
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_exponential,
)

from models.job import Job
from models.scenario import CareersPageScenario, JobPageScenario
from pyrate_limiter import Limiter

REQUEST = "request"

logger = logging.getLogger(__name__)


@dataclass
class ScrapeResult:
    jobs: list[Job] = field(default_factory=list)
    deleted_urls: list[str] = field(default_factory=list)


class ScrapingEngine:
    def __init__(
        self,
        context: BrowserContext,
        rate_limiter: Limiter,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ):
        self.context = context
        self.rate_limiter = rate_limiter
        self._retry_kwargs = dict(
            wait=wait_exponential(multiplier=retry_base_delay),
            stop=stop_after_attempt(max_retries),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )

    async def scrape_site(
        self,
        url: str,
        company: str,
        careers: CareersPageScenario,
        job_page: JobPageScenario,
        limit: int = None,
        known_urls: set[str] = None,
    ) -> ScrapeResult:
        urls = await retry(**self._retry_kwargs)(self._collect_job_urls)(
            url, careers, limit
        )
        known_urls = known_urls or set()
        new_urls = urls - known_urls
        deleted_urls = list(known_urls - urls)
        jobs = []
        for job_url in new_urls:
            job = await retry(**self._retry_kwargs)(self._scrape_job)(
                job_url, company, job_page
            )
            if job is not None:
                jobs.append(job)
        return ScrapeResult(jobs=jobs, deleted_urls=deleted_urls)

    async def _collect_job_urls(
        self, url: str, scenario: CareersPageScenario, limit: int = None
    ) -> set[str]:
        await self._limit_request()
        page = await self.context.new_page()
        try:
            logger.info("Collecting job urls from %s", url)
            response = await page.goto(url, wait_until="domcontentloaded")
            if not response.ok:
                raise Exception(f"Failed to go to page {url}, status {response.status}")
            urls: set[str] = set()

            while True:
                cards = await page.query_selector_all(scenario.job_card_selector)
                for card in cards:
                    link = await card.query_selector(scenario.job_link_selector)
                    if link is None:
                        continue
                    href = await link.get_attribute("href")
                    if href is None:
                        continue
                    absolute = urllib.parse.urljoin(url, href)
                    urls.add(absolute)
                    if limit is not None and len(urls) >= limit:
                        break

                if limit is not None and len(urls) >= limit:
                    break

                if not scenario.next_page_selector:
                    break

                next_btn = await page.query_selector(scenario.next_page_selector)
                if next_btn is None:
                    break

                disabled = await next_btn.get_attribute(
                    scenario.next_page_disabled_attr
                )
                if disabled == scenario.next_page_disabled_value:
                    break

                await self._limit_request()
                await next_btn.click()
                logger.info("Clicked next page: %s", page.url)
                await page.wait_for_load_state("domcontentloaded")

            return urls
        finally:
            await page.close()

    async def _scrape_job(
        self, url: str, company: str, scenario: JobPageScenario
    ) -> Job | None:
        await self._limit_request()
        page = await self.context.new_page()
        try:
            logger.info("Scraping job %s", url)
            await page.goto(url, wait_until="domcontentloaded")

            title = await self._extract_field(page, scenario.title_selectors)
            location = await self._extract_field(page, scenario.location_selectors)
            description = await self._extract_field(
                page, scenario.description_selectors, use_inner_text=True
            )

            if not title:
                return None

            return Job(
                company=company,
                url=url,
                title=title,
                location=location or "",
                description=description or "",
            )
        finally:
            await page.close()

    async def _extract_field(
        self, page, selectors: list[str], use_inner_text: bool = False
    ) -> str | None:
        for selector in selectors:
            el = await page.query_selector(selector)
            if el is None:
                continue
            tag = await el.evaluate("e => e.tagName.toLowerCase()")
            if tag == "meta":
                value = await el.get_attribute("content")
            elif use_inner_text:
                value = await el.inner_text()
            else:
                value = await el.text_content()
            if value:
                return value.strip()
        return None

    async def _limit_request(self):
        await self.rate_limiter.try_acquire_async(REQUEST)
