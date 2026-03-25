import asyncio
import json
import time
from pathlib import Path

import pytest
import pytest_asyncio
from testcontainers.core.container import DockerContainer, LogMessageWaitStrategy

from models.company import Company
from models.config import DynamoDbConfig, SqsConfig
from queues.sqs_queue import SqsQueue
from storage.dynamodb_storage import DynamoDbStorage
from test.conftest import run_mock_server, ALL_JOBS

pytestmark = pytest.mark.integration

CONFIGS_TABLE = "test-configs"
JOBS_TABLE = "test-jobs"
REGION = "us-east-1"
DYNAMODB_PORT = 8000
ELASTICMQ_PORT = 9324
QUEUE_NAME = "test-scraper-queue"
HOST_DOCKER_INTERNAL = "host.docker.internal"


@pytest.fixture(scope="session")
def docker_image():
    """Build the scraper Docker image once per test session."""
    import subprocess

    tag = "job-prospector-scraper:test"
    result = subprocess.run(
        ["docker", "build", "-t", tag, "-f", "docker/Dockerfile", "."],
        cwd=str(Path(__file__).parent.parent.parent),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(f"Docker build failed:\n{result.stderr}")
    return tag


@pytest.fixture(scope="session")
def dynamodb_container():
    container = DockerContainer("amazon/dynamodb-local:latest").with_exposed_ports(
        DYNAMODB_PORT
    )
    with container:
        container.waiting_for(
            LogMessageWaitStrategy("CorsParams").with_startup_timeout(30)
        )
        yield container


@pytest.fixture(scope="session")
def elasticmq_container():
    container = DockerContainer(
        "softwaremill/elasticmq-native:latest"
    ).with_exposed_ports(ELASTICMQ_PORT)
    with container:
        container.waiting_for(
            LogMessageWaitStrategy("started").with_startup_timeout(30)
        )
        yield container


@pytest.fixture
def dynamodb_storage(dynamodb_container, monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    endpoint_url = f"http://{dynamodb_container.get_container_host_ip()}:{dynamodb_container.get_exposed_port(DYNAMODB_PORT)}"

    storage = DynamoDbStorage(
        DynamoDbConfig(
            configs_table=CONFIGS_TABLE,
            jobs_table=JOBS_TABLE,
            region=REGION,
            endpoint_url=endpoint_url,
        )
    )
    storage.create_tables()
    yield storage

    storage.dynamodb.Table(CONFIGS_TABLE).delete()
    storage.dynamodb.Table(JOBS_TABLE).delete()


@pytest.fixture
def sqs_queue(elasticmq_container):
    import boto3

    endpoint_url = f"http://{elasticmq_container.get_container_host_ip()}:{elasticmq_container.get_exposed_port(ELASTICMQ_PORT)}"
    client = boto3.client(
        "sqs",
        region_name=REGION,
        endpoint_url=endpoint_url,
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
    )
    response = client.create_queue(QueueName=QUEUE_NAME)
    queue_url = response["QueueUrl"]

    queue = SqsQueue(
        SqsConfig(
            queue_url=queue_url,
            region=REGION,
            wait_time_seconds=1,
            endpoint_url=endpoint_url,
        )
    )
    yield queue

    client.delete_queue(QueueUrl=queue_url)


@pytest_asyncio.fixture
async def mock_target_server():
    """Mock server exposed to Docker containers via host.docker.internal."""
    async with run_mock_server(
        bind_host="0.0.0.0", url_host=HOST_DOCKER_INTERNAL
    ) as base_url:
        yield base_url


async def _wait_for_jobs(dynamodb_storage, company, expected_count, timeout=30):
    """Poll DynamoDB until the expected number of jobs appear."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        jobs = dynamodb_storage.list_jobs(company)
        if len(jobs) >= expected_count:
            return jobs
        await asyncio.sleep(1)
    raise TimeoutError(
        f"Expected {expected_count} jobs for {company}, "
        f"got {len(dynamodb_storage.list_jobs(company))} after {timeout}s"
    )


async def test_scraper_container(
    docker_image,
    mock_target_server,
    dynamodb_container,
    dynamodb_storage,
    elasticmq_container,
    sqs_queue,
    fixtures_dir,
):
    base_url = mock_target_server

    # Send company config to SQS queue
    site_data = json.loads(fixtures_dir.joinpath("site.json").read_text())
    site_data["url"] = f"{base_url}/careers/"
    company = Company.from_dict(site_data)
    await sqs_queue.send_message(company)

    # Build the SQS queue URL as seen from inside Docker
    elasticmq_docker_url = f"http://{HOST_DOCKER_INTERNAL}:{elasticmq_container.get_exposed_port(ELASTICMQ_PORT)}"
    sqs_queue_url = f"{elasticmq_docker_url}/000000000000/{QUEUE_NAME}"

    container = (
        DockerContainer(docker_image)
        .with_env("SCRAPER_STORAGE_TYPE", "dynamodb")
        .with_env("DYNAMODB_CONFIGS_TABLE", CONFIGS_TABLE)
        .with_env("DYNAMODB_JOBS_TABLE", JOBS_TABLE)
        .with_env("DYNAMODB_REGION", REGION)
        .with_env(
            "DYNAMODB_ENDPOINT_URL",
            f"http://{HOST_DOCKER_INTERNAL}:{dynamodb_container.get_exposed_port(DYNAMODB_PORT)}",
        )
        .with_env("SQS_QUEUE_URL", sqs_queue_url)
        .with_env("SQS_REGION", REGION)
        .with_env("SQS_ENDPOINT_URL", elasticmq_docker_url)
        .with_env("SQS_WAIT_TIME_SECONDS", "1")
        .with_env("AWS_ACCESS_KEY_ID", "testing")
        .with_env("AWS_SECRET_ACCESS_KEY", "testing")
        .with_env("SCRAPER_RPS", "1000")
        .with_kwargs(extra_hosts={HOST_DOCKER_INTERNAL: "host-gateway"})
    )

    with container:
        jobs = await _wait_for_jobs(dynamodb_storage, "Acme Corp", len(ALL_JOBS))
        assert {(job.title, job.location) for job in jobs} == {
            (job["title"], job["location"]) for job in ALL_JOBS
        }
