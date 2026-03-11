from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from aiohttp import web
from jinja2 import Environment, FileSystemLoader

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@asynccontextmanager
async def run_mock_server(*, bind_host="127.0.0.1", url_host=None):
    """Start a mock job-board server.

    Args:
        bind_host: Interface to bind on (use "0.0.0.0" to expose to Docker).
        url_host: Hostname used in rendered URLs. Defaults to bind_host.
    """
    if url_host is None:
        url_host = bind_host

    jinja_env = Environment(loader=FileSystemLoader(str(FIXTURES_DIR)))
    index_template = jinja_env.get_template("index.html.j2")
    job_html = FIXTURES_DIR.joinpath("job.html.j2").read_text()

    app = web.Application()
    rendered_index = None

    async def handle_index(_request):
        return web.Response(text=rendered_index, content_type="text/html")

    async def handle_job(_request):
        return web.Response(text=job_html, content_type="text/html")

    app.router.add_get("/", handle_index)
    app.router.add_get("/careers/", handle_index)
    app.router.add_get("/careers/jobs/{job_id}", handle_job)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, bind_host, 0)
    await site.start()

    port = site._server.sockets[0].getsockname()[1]
    base_url = f"http://{url_host}:{port}"

    rendered_index = index_template.render(base_url=base_url)

    try:
        yield base_url
    finally:
        await runner.cleanup()
