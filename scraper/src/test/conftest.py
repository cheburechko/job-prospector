import math
from contextlib import asynccontextmanager
from pathlib import Path

import aioboto3
import pytest
from aiohttp import web
from jinja2 import Environment, FileSystemLoader
from testcontainers.core.container import DockerContainer, LogMessageWaitStrategy

from models.config import DynamoDbConfig, SqsConfig
from sqs_queue import SqsQueue
from dynamodb_storage import DynamoDbStorage

FIXTURES_DIR = Path(__file__).parent / "fixtures"
DYNAMODB_PORT = 8000
ELASTICMQ_PORT = 9324
REGION = "us-east-1"
CONFIGS_TABLE = "test-configs"
JOBS_TABLE = "test-jobs"
QUEUE_NAME = "test-queue"

ALL_JOBS = [
    {"id": "1001", "title": "Software Engineer", "location": "Berlin, Germany"},
    {"id": "1002", "title": "Product Manager", "location": "Hamburg, Germany"},
    {"id": "1003", "title": "Data Analyst", "location": "Munich, Germany"},
]


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def dynamodb_container():
    container = DockerContainer("amazon/dynamodb-local:latest").with_exposed_ports(
        DYNAMODB_PORT
    )
    with container:
        container.waiting_for(
            LogMessageWaitStrategy("CorsParams")
            .with_startup_timeout(30)
            .with_poll_interval(0.1)
        )
        yield container


@pytest.fixture(scope="session")
def elasticmq_container():
    container = DockerContainer(
        "softwaremill/elasticmq-native:latest"
    ).with_exposed_ports(ELASTICMQ_PORT)
    with container:
        container.waiting_for(
            LogMessageWaitStrategy("started")
            .with_startup_timeout(30)
            .with_poll_interval(0.1)
        )
        yield container


@pytest.fixture
async def dynamodb_storage(dynamodb_container, monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    endpoint_url = f"http://{dynamodb_container.get_container_host_ip()}:{dynamodb_container.get_exposed_port(DYNAMODB_PORT)}"

    async with DynamoDbStorage(
        DynamoDbConfig(
            configs_table=CONFIGS_TABLE,
            jobs_table=JOBS_TABLE,
            region=REGION,
            endpoint_url=endpoint_url,
        )
    ) as storage:
        await storage.create_tables()
        yield storage

        table = await storage.dynamodb.Table(CONFIGS_TABLE)
        await table.delete()
        table = await storage.dynamodb.Table(JOBS_TABLE)
        await table.delete()


@pytest.fixture
async def sqs_queue(elasticmq_container, monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    endpoint_url = f"http://{elasticmq_container.get_container_host_ip()}:{elasticmq_container.get_exposed_port(ELASTICMQ_PORT)}"

    session = aioboto3.Session()
    async with session.client(
        "sqs",
        region_name=REGION,
        endpoint_url=endpoint_url,
    ) as client:
        response = await client.create_queue(
            QueueName=QUEUE_NAME,
            Attributes={"VisibilityTimeout": "1"},
        )
        queue_url = response["QueueUrl"]

        async with SqsQueue(
            SqsConfig(
                queue_url=queue_url,
                region=REGION,
                wait_time_seconds=0,
                max_messages=10,
                endpoint_url=endpoint_url,
            )
        ) as queue:
            yield queue

        await client.delete_queue(QueueUrl=queue_url)


@asynccontextmanager
async def run_mock_server(
    *, bind_host="127.0.0.1", url_host=None, page_size=None, fail_times=0
):
    """Start a mock job-board server.

    Args:
        bind_host: Interface to bind on (use "0.0.0.0" to expose to Docker).
        url_host: Hostname used in rendered URLs. Defaults to bind_host.
        page_size: When set, enables pagination with this many jobs per page.
        fail_times: Number of initial requests that return 500 before succeeding.
    """
    if url_host is None:
        url_host = bind_host

    jinja_env = Environment(loader=FileSystemLoader(str(FIXTURES_DIR)))
    index_template = jinja_env.get_template("index.html.j2")
    job_template = jinja_env.get_template("job.html.j2")
    jobs_by_id = {job["id"]: job for job in ALL_JOBS}

    app = web.Application()
    base_url_ref: list[str] = []
    request_count = [0]

    @web.middleware
    async def fail_middleware(request, handler):
        if request_count[0] < fail_times:
            request_count[0] += 1
            return web.Response(status=500, text="Internal Server Error")
        return await handler(request)

    app.middlewares.append(fail_middleware)

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
