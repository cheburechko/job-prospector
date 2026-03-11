import pytest
import pytest_asyncio
from playwright.async_api import async_playwright

from rate_limiter import RateLimiter
from test.conftest import run_mock_server


@pytest_asyncio.fixture
async def mock_server():
    async with run_mock_server(bind_host="127.0.0.1") as base_url:
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
    return RateLimiter(rps=1000.0)
