import pytest
import pytest_asyncio
from playwright.async_api import async_playwright

from models.company import Company
from models.scenario import CareersPageScenario, JobPageScenario
from pyrate_limiter import Duration, Rate, InMemoryBucket, Limiter
from test.conftest import run_mock_server


@pytest_asyncio.fixture
async def mock_server():
    async with run_mock_server(bind_host="127.0.0.1") as base_url:
        yield base_url


@pytest_asyncio.fixture
async def paginated_mock_server():
    async with run_mock_server(bind_host="127.0.0.1", page_size=2) as base_url:
        yield base_url


@pytest_asyncio.fixture
async def browser_context():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        yield context
        await context.close()
        await browser.close()


@pytest.fixture
def rate_limiter():
    bucket = InMemoryBucket([Rate(1000, Duration.SECOND)])
    return Limiter(bucket)


@pytest.fixture
def company():
    return Company(
        company="Acme",
        url="https://example.com/jobs",
        careers_page=CareersPageScenario(
            job_card_selector="div.job",
            job_link_selector="a",
        ),
        job_page=JobPageScenario(
            title_selectors=["h1"],
            location_selectors=[".loc"],
            description_selectors=[".desc"],
        ),
    )
