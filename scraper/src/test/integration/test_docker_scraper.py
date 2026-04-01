import asyncio
import json
import logging
import time
from pathlib import Path

import pytest
import pytest_asyncio
from testcontainers.core.container import DockerContainer

from models.company import Company
from test.conftest import (
    run_mock_server,
    ALL_JOBS,
    CONFIGS_TABLE,
    JOBS_TABLE,
    QUEUE_NAME,
    DYNAMODB_PORT,
    ELASTICMQ_PORT,
    REGION,
)

pytestmark = pytest.mark.integration

HOST_DOCKER_INTERNAL = "host.docker.internal"

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def docker_image():
    """Build the scraper Docker image once per test session."""
    import subprocess

    tag = "job-prospector-scraper:test"
    result = subprocess.run(
        ["docker", "build", "-t", tag, "-f", "docker/Dockerfile", "."],
        cwd=str(Path(__file__).parent.parent.parent.parent),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(f"Docker build failed:\n{result.stderr}")
    return tag


@pytest_asyncio.fixture
async def mock_target_server():
    """Mock server exposed to Docker containers via host.docker.internal."""
    async with run_mock_server(
        bind_host="0.0.0.0", url_host=HOST_DOCKER_INTERNAL
    ) as base_url:
        yield base_url


def _make_container(docker_image, dynamodb_container, elasticmq_container):
    """Create a DockerContainer with shared AWS env vars."""
    dynamodb_url = f"http://{HOST_DOCKER_INTERNAL}:{dynamodb_container.get_exposed_port(DYNAMODB_PORT)}"
    elasticmq_url = f"http://{HOST_DOCKER_INTERNAL}:{elasticmq_container.get_exposed_port(ELASTICMQ_PORT)}"
    sqs_queue_url = f"{elasticmq_url}/000000000000/{QUEUE_NAME}"

    return (
        DockerContainer(docker_image)
        .with_env("DYNAMODB_CONFIGS_TABLE", CONFIGS_TABLE)
        .with_env("DYNAMODB_JOBS_TABLE", JOBS_TABLE)
        .with_env("DYNAMODB_REGION", REGION)
        .with_env("DYNAMODB_ENDPOINT_URL", dynamodb_url)
        .with_env("SQS_QUEUE_URL", sqs_queue_url)
        .with_env("SQS_REGION", REGION)
        .with_env("SQS_ENDPOINT_URL", elasticmq_url)
        .with_env("AWS_ACCESS_KEY_ID", "testing")
        .with_env("AWS_SECRET_ACCESS_KEY", "testing")
        .with_kwargs(extra_hosts={HOST_DOCKER_INTERNAL: "host-gateway"})
    )


async def _wait_for_jobs(dynamodb_storage, company, expected_count, timeout=30):
    """Poll DynamoDB until the expected number of jobs appear."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        jobs = await dynamodb_storage.list_jobs(company)
        if len(jobs) >= expected_count:
            return jobs
        await asyncio.sleep(1)
    return None


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

    # Add company to storage (scheduler will send it to the queue)
    site_data = json.loads(fixtures_dir.joinpath("site.json").read_text())
    site_data["url"] = f"{base_url}/careers/"
    company = Company.from_dict(site_data)
    async with dynamodb_storage.company_writer() as writer:
        await writer.add(company)

    scheduler = _make_container(
        docker_image, dynamodb_container, elasticmq_container
    ).with_command("scheduler")
    worker = (
        _make_container(docker_image, dynamodb_container, elasticmq_container)
        .with_command("worker")
        .with_env("SCRAPER_RPS", "1000")
        .with_env("SCRAPER_SQS_WAIT_TIME_SECONDS", "1")
    )
    with scheduler, worker:
        jobs = await _wait_for_jobs(dynamodb_storage, "Acme Corp", len(ALL_JOBS), 10)
        if jobs is None:
            logger.error("No jobs found")
            logger.error("Scheduler logs: %s", scheduler.get_logs())
            logger.error("Worker logs: %s", worker.get_logs())
            pytest.fail("No jobs found")
        assert {(job.title, job.location) for job in jobs} == {
            (job["title"], job["location"]) for job in ALL_JOBS
        }
