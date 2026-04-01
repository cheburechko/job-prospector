import pytest
import pytest_asyncio

from models.scenario import CareersPageScenario, JobPageScenario
from template.engine import ScrapeResult, ScrapingEngine
from test.conftest import run_mock_server

pytestmark = pytest.mark.asyncio

CAREERS_SCENARIO = CareersPageScenario(
    job_card_selector="tr.job-post",
    job_link_selector="a",
)

PAGINATED_CAREERS_SCENARIO = CareersPageScenario(
    job_card_selector="tr.job-post",
    job_link_selector="a",
    next_page_selector="button.pagination__next",
    next_page_disabled_attr="aria-disabled",
    next_page_disabled_value="true",
)

JOB_SCENARIO = JobPageScenario(
    title_selectors=["h1.section-header", 'meta[property="og:title"]'],
    location_selectors=[".job__location div", 'meta[property="og:description"]'],
    description_selectors=[".job__description"],
)


async def test_collect_job_urls(mock_server, browser_context, rate_limiter):
    engine = ScrapingEngine(browser_context, rate_limiter)
    urls = await engine._collect_job_urls(f"{mock_server}/careers/", CAREERS_SCENARIO)
    assert {
        f"{mock_server}/careers/jobs/{job_id}" for job_id in ("1001", "1002", "1003")
    } == urls


async def test_scrape_job(mock_server, browser_context, rate_limiter):
    engine = ScrapingEngine(browser_context, rate_limiter)
    job = await engine._scrape_job(
        f"{mock_server}/careers/jobs/1001", "Acme Corp", JOB_SCENARIO
    )
    assert job is not None
    assert job.company == "Acme Corp"
    assert job.url == f"{mock_server}/careers/jobs/1001"
    assert job.title == "Software Engineer"
    assert job.location == "Berlin, Germany"
    assert len(job.description) > 0


async def test_scrape_site_full(mock_server, browser_context, rate_limiter):
    engine = ScrapingEngine(browser_context, rate_limiter)
    result = await engine.scrape_site(
        url=f"{mock_server}/careers/",
        company="Acme Corp",
        careers=CAREERS_SCENARIO,
        job_page=JOB_SCENARIO,
    )
    assert isinstance(result, ScrapeResult)
    assert len(result.jobs) == 3
    assert result.deleted_urls == []
    for job in result.jobs:
        assert job.company == "Acme Corp"
    titles = {job.title for job in result.jobs}
    assert titles == {"Software Engineer", "Product Manager", "Data Analyst"}


async def test_scrape_site_skips_known_urls(mock_server, browser_context, rate_limiter):
    engine = ScrapingEngine(browser_context, rate_limiter)
    known_urls = {f"{mock_server}/careers/jobs/1001"}
    result = await engine.scrape_site(
        url=f"{mock_server}/careers/",
        company="Acme Corp",
        careers=CAREERS_SCENARIO,
        job_page=JOB_SCENARIO,
        known_urls=known_urls,
    )
    assert len(result.jobs) == 2
    assert result.deleted_urls == []
    scraped_urls = {job.url for job in result.jobs}
    assert f"{mock_server}/careers/jobs/1001" not in scraped_urls


async def test_scrape_site_detects_deleted_urls(
    mock_server, browser_context, rate_limiter
):
    engine = ScrapingEngine(browser_context, rate_limiter)
    removed_url = f"{mock_server}/careers/jobs/9999"
    known_urls = {f"{mock_server}/careers/jobs/1001", removed_url}
    result = await engine.scrape_site(
        url=f"{mock_server}/careers/",
        company="Acme Corp",
        careers=CAREERS_SCENARIO,
        job_page=JOB_SCENARIO,
        known_urls=known_urls,
    )
    assert len(result.jobs) == 2
    assert result.deleted_urls == [removed_url]


async def test_collect_job_urls_with_pagination(
    paginated_mock_server, browser_context, rate_limiter
):
    engine = ScrapingEngine(browser_context, rate_limiter)
    urls = await engine._collect_job_urls(
        f"{paginated_mock_server}/careers/", PAGINATED_CAREERS_SCENARIO
    )
    assert {
        f"{paginated_mock_server}/careers/jobs/{job_id}"
        for job_id in ("1001", "1002", "1003")
    } == urls


@pytest_asyncio.fixture
async def flaky_mock_server():
    async with run_mock_server(bind_host="127.0.0.1", fail_times=2) as base_url:
        yield base_url


async def test_scrape_site_retries_on_failure(
    flaky_mock_server, browser_context, rate_limiter
):
    engine = ScrapingEngine(
        browser_context, rate_limiter, max_retries=3, retry_base_delay=0.01
    )
    result = await engine.scrape_site(
        url=f"{flaky_mock_server}/careers/",
        company="Acme Corp",
        careers=CAREERS_SCENARIO,
        job_page=JOB_SCENARIO,
    )
    assert len(result.jobs) == 3


async def test_scrape_site_fails_after_max_retries(
    flaky_mock_server, browser_context, rate_limiter
):
    engine = ScrapingEngine(
        browser_context, rate_limiter, max_retries=1, retry_base_delay=0.01
    )
    with pytest.raises(Exception):
        await engine.scrape_site(
            url=f"{flaky_mock_server}/careers/",
            company="Acme Corp",
            careers=CAREERS_SCENARIO,
            job_page=JOB_SCENARIO,
        )
