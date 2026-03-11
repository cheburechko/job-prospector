import pytest

from models.scenario import CareersPageScenario, JobPageScenario
from template.engine import ScrapingEngine

pytestmark = pytest.mark.asyncio

# Scenario without pagination for mock tests (mock doesn't support real pagination)
CAREERS_SCENARIO = CareersPageScenario(
    job_card_selector="tr.job-post",
    job_link_selector="a",
)

JOB_SCENARIO = JobPageScenario(
    title_selectors=["h1.section-header", 'meta[property="og:title"]'],
    location_selectors=[".job__location div", 'meta[property="og:description"]'],
    description_selectors=[".job__description"],
)


async def test_collect_job_urls(mock_server, browser_context, rate_limiter):
    engine = ScrapingEngine(browser_context, rate_limiter)
    urls = await engine._collect_job_urls(f"{mock_server}/careers/", CAREERS_SCENARIO)
    assert len(urls) > 0
    # All URLs should point to the mock server
    for url in urls:
        assert mock_server in url
    # First job should be Software Engineer
    assert "/careers/jobs/1001" in urls[0]


async def test_scrape_job(mock_server, browser_context, rate_limiter):
    engine = ScrapingEngine(browser_context, rate_limiter)
    job = await engine._scrape_job(
        f"{mock_server}/careers/jobs/1001", "Acme Corp", JOB_SCENARIO
    )
    assert job is not None
    assert job.company == "Acme Corp"
    assert job.title == "Software Engineer"
    assert job.location == "Berlin, Germany"
    assert len(job.description) > 0


async def test_scrape_site_full(mock_server, browser_context, rate_limiter):
    engine = ScrapingEngine(browser_context, rate_limiter)
    jobs = await engine.scrape_site(
        url=f"{mock_server}/careers/",
        company="Acme Corp",
        careers=CAREERS_SCENARIO,
        job_page=JOB_SCENARIO,
    )
    assert len(jobs) > 0
    # All jobs served by mock return the same job.html.j2
    for job in jobs:
        assert job.company == "Acme Corp"
        assert job.title == "Software Engineer"
