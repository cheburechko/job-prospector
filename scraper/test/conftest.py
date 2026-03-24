import math
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from aiohttp import web
from jinja2 import Environment, FileSystemLoader

FIXTURES_DIR = Path(__file__).parent / "fixtures"

ALL_JOBS = [
    {"id": "1001", "title": "Software Engineer", "location": "Berlin, Germany"},
    {"id": "1002", "title": "Product Manager", "location": "Hamburg, Germany"},
    {"id": "1003", "title": "Data Analyst", "location": "Munich, Germany"},
]


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@asynccontextmanager
async def run_mock_server(*, bind_host="127.0.0.1", url_host=None, page_size=None):
    """Start a mock job-board server.

    Args:
        bind_host: Interface to bind on (use "0.0.0.0" to expose to Docker).
        url_host: Hostname used in rendered URLs. Defaults to bind_host.
        page_size: When set, enables pagination with this many jobs per page.
    """
    if url_host is None:
        url_host = bind_host

    jinja_env = Environment(loader=FileSystemLoader(str(FIXTURES_DIR)))
    index_template = jinja_env.get_template("index.html.j2")
    job_template = jinja_env.get_template("job.html.j2")
    jobs_by_id = {job["id"]: job for job in ALL_JOBS}

    app = web.Application()
    base_url_ref: list[str] = []

    async def handle_index(request):
        base_url = base_url_ref[0]

        if page_size is None:
            jobs = ALL_JOBS
            next_page_url = None
            show_disabled_next = False
        else:
            page = int(request.query.get("page", "1"))
            total_pages = math.ceil(len(ALL_JOBS) / page_size)
            start = (page - 1) * page_size
            jobs = ALL_JOBS[start : start + page_size]

            if page < total_pages:
                next_page_url = f"{base_url}/careers/?page={page + 1}"
                show_disabled_next = False
            else:
                next_page_url = None
                show_disabled_next = True

        rendered = index_template.render(
            base_url=base_url,
            jobs=jobs,
            next_page_url=next_page_url,
            show_disabled_next=show_disabled_next,
        )
        return web.Response(text=rendered, content_type="text/html")

    async def handle_job(request):
        job_id = request.match_info["job_id"]
        job = jobs_by_id.get(job_id)
        if job is None:
            return web.Response(status=404)
        rendered = job_template.render(title=job["title"], location=job["location"])
        return web.Response(text=rendered, content_type="text/html")

    app.router.add_get("/", handle_index)
    app.router.add_get("/careers/", handle_index)
    app.router.add_get("/careers/jobs/{job_id}", handle_job)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, bind_host, 0)
    await site.start()

    port = site._server.sockets[0].getsockname()[1]
    base_url = f"http://{url_host}:{port}"
    base_url_ref.append(base_url)

    try:
        yield base_url
    finally:
        await runner.cleanup()
