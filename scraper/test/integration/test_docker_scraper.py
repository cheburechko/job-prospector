import json
import time
from pathlib import Path

import pytest
import pytest_asyncio
from testcontainers.core.container import DockerContainer

from test.conftest import FIXTURES_DIR, run_mock_server

pytestmark = pytest.mark.integration


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


@pytest_asyncio.fixture
async def mock_target_server():
    """Mock server exposed to Docker containers via host.docker.internal."""
    async with run_mock_server(
        bind_host="0.0.0.0", url_host="host.docker.internal"
    ) as base_url:
        yield base_url


def _wait_for_container_exit(container, timeout=120):
    """Poll the container until it exits or timeout is reached."""
    import docker

    client = docker.from_env()
    c = client.containers.get(container._container.id)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        c.reload()
        if c.status in ("exited", "dead"):
            return c.attrs["State"]["ExitCode"]
        time.sleep(1)
    raise TimeoutError(f"Container did not exit within {timeout}s")


async def test_scraper_container(docker_image, mock_target_server, tmp_path):
    base_url = mock_target_server

    # Prepare site config with URL pointing to mock server
    sites_dir = tmp_path / "sites"
    sites_dir.mkdir()

    wolt_config = json.loads(FIXTURES_DIR.joinpath("wolt.json").read_text())
    wolt_config["url"] = f"{base_url}/wolt/"
    (sites_dir / "wolt.json").write_text(json.dumps(wolt_config))

    output_path = tmp_path / "output.json"

    container = (
        DockerContainer(docker_image)
        .with_volume_mapping(str(sites_dir), "/data/sites", "ro")
        .with_volume_mapping(str(tmp_path), "/data/output", "rw")
        .with_env("SCRAPER_SITES_DIR", "/data/sites")
        .with_env("SCRAPER_OUTPUT_PATH", "/data/output/output.json")
        .with_kwargs(extra_hosts={"host.docker.internal": "host-gateway"})
    )

    with container:
        exit_code = _wait_for_container_exit(container)
        logs = container.get_logs()
        assert exit_code == 0, f"Container exited with code {exit_code}:\n{logs}"

        assert output_path.exists(), f"output.json was not created. Logs:\n{logs}"
        jobs = json.loads(output_path.read_text())
        assert len(jobs) > 0, "No jobs were scraped"
        assert jobs[0]["company"] == "Wolt"
        assert jobs[0]["title"] == "Support Associate"
