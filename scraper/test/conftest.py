import re
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from aiohttp import web

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@asynccontextmanager
async def run_mock_server(*, bind_host="127.0.0.1", url_host=None):
    """Start a mock Greenhouse server.

    Args:
        bind_host: Interface to bind on (use "0.0.0.0" to expose to Docker).
        url_host: Hostname used in rewritten URLs. Defaults to bind_host.
    """
    if url_host is None:
        url_host = bind_host

    index_html = FIXTURES_DIR.joinpath("index.htm").read_text()
    job_html = FIXTURES_DIR.joinpath("job.htm").read_text()

    app = web.Application()
    rewritten_index = None

    async def handle_index(_request):
        return web.Response(text=rewritten_index, content_type="text/html")

    async def handle_job(_request):
        return web.Response(text=job_html, content_type="text/html")

    app.router.add_get("/", handle_index)
    app.router.add_get("/wolt/", handle_index)
    app.router.add_get("/wolt/jobs/{job_id}", handle_job)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, bind_host, 0)
    await site.start()

    port = site._server.sockets[0].getsockname()[1]
    base_url = f"http://{url_host}:{port}"

    rewritten_index = re.sub(
        r"https?://job-boards\.greenhouse\.io",
        base_url,
        index_html,
    )

    try:
        yield base_url
    finally:
        await runner.cleanup()
