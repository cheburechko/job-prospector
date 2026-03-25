import asyncio
import json
import time
from pathlib import Path

import pytest
import pytest_asyncio
from testcontainers.core.container import DockerContainer, LogMessageWaitStrategy

from storage.dynamodb_storage import DynamoDbStorage
from models.company import Company
from test.conftest import run_mock_server, ALL_JOBS

pytestmark = pytest.mark.integration

CONFIGS_TABLE = "test-configs"
JOBS_TABLE = "test-jobs"
REGION = "us-east-1"
DYNAMODB_PORT = 8000
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


@pytest.fixture
def dynamodb_storage(dynamodb_container, monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)
    endpoint_url = f"http://{dynamodb_container.get_container_host_ip()}:{dynamodb_container.get_exposed_port(DYNAMODB_PORT)}"

    storage = DynamoDbStorage(
        configs_table=CONFIGS_TABLE,
        jobs_table=JOBS_TABLE,
        region=REGION,
        endpoint_url=endpoint_url,
    )
    storage.create_tables()
    yield storage

    storage.dynamodb.Table(CONFIGS_TABLE).delete()
    storage.dynamodb.Table(JOBS_TABLE).delete()


@pytest_asyncio.fixture
async def mock_target_server():
    """Mock server exposed to Docker containers via host.docker.internal."""
    async with run_mock_server(
        bind_host="0.0.0.0", url_host=HOST_DOCKER_INTERNAL
    ) as base_url:
        yield base_url


async def _wait_for_container_exit(container, timeout=15):
    """Poll the container until it exits or timeout is reached."""
    import docker

    client = docker.from_env()
    c = client.containers.get(container._container.id)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        c.reload()
        if c.status in ("exited", "dead"):
            return c.attrs["State"]["ExitCode"]
        await asyncio.sleep(1)
    raise TimeoutError(f"Container did not exit within {timeout}s")


async def test_scraper_container(
    docker_image, mock_target_server, dynamodb_container, dynamodb_storage, fixtures_dir
):
    base_url = mock_target_server

    # Load company config into DynamoDB
    site_data = json.loads(fixtures_dir.joinpath("site.json").read_text())
    site_data["url"] = f"{base_url}/careers/"
    company = Company.from_dict(site_data)
    dynamodb_storage.add_company(company)

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
        .with_env("AWS_ACCESS_KEY_ID", "testing")
        .with_env("AWS_SECRET_ACCESS_KEY", "testing")
        .with_env("SCRAPER_RPS", "1000")
        .with_kwargs(extra_hosts={HOST_DOCKER_INTERNAL: "host-gateway"})
    )

    with container:
        exit_code = await _wait_for_container_exit(container)
        stdout, stderr = container.get_logs()
        assert exit_code == 0, (
            f"Container exited with code {exit_code}:\nstdout:\n{stdout}\nstderr:\n{stderr}"
        )

        jobs = dynamodb_storage.list_jobs("Acme Corp")
        assert {(job.title, job.location) for job in jobs} == {
            (job["title"], job["location"]) for job in ALL_JOBS
        }
