import re
from pathlib import Path

import pytest
import pytest_asyncio
from aiohttp import web
from playwright.async_api import async_playwright

from rate_limiter import RateLimiter

DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture
def data_dir():
    return DATA_DIR


@pytest_asyncio.fixture
async def mock_server():
    index_html = DATA_DIR.joinpath("index.htm").read_text()
    job_html = DATA_DIR.joinpath("job.htm").read_text()

    host = "127.0.0.1"
    app = web.Application()

    # Will be set once the server starts and we know the port
    rewritten_index = None

    async def handle_index(request):
        return web.Response(text=rewritten_index, content_type="text/html")

    async def handle_job(request):
        return web.Response(text=job_html, content_type="text/html")

    app.router.add_get("/", handle_index)
    app.router.add_get("/wolt/", handle_index)
    app.router.add_get("/wolt/jobs/{job_id}", handle_job)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, 0)
    await site.start()

    port = site._server.sockets[0].getsockname()[1]
    base_url = f"http://{host}:{port}"

    # Rewrite absolute greenhouse URLs to point to local server
    rewritten_index = re.sub(
        r"https?://job-boards\.greenhouse\.io",
        base_url,
        index_html,
    )

    yield base_url

    await runner.cleanup()


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
