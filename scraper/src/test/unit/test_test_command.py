import json

import pytest

from commands.test import run_test
from commands.test import TestConfig
from test.conftest import ALL_JOBS, run_mock_server

pytestmark = pytest.mark.asyncio


@pytest.fixture
def input_data(fixtures_dir):
    data = json.loads(fixtures_dir.joinpath("site.json").read_text())
    data["url"] = "PLACEHOLDER"
    return data


async def test_run_test_scrapes_and_writes_output(input_data, tmp_path):
    output_file = tmp_path / "out.json"
    input_file = tmp_path / "input.json"

    async with run_mock_server(bind_host="127.0.0.1") as base_url:
        input_data["url"] = f"{base_url}/careers/"
        input_file.write_text(json.dumps(input_data))

        config = TestConfig(input=str(input_file), output=str(output_file))
        await run_test(config)

    result = json.loads(output_file.read_text())
    assert len(result) == len(ALL_JOBS)

    titles = {job["title"] for job in result}
    assert titles == {j["title"] for j in ALL_JOBS}

    locations = {job["location"] for job in result}
    assert locations == {j["location"] for j in ALL_JOBS}

    for job in result:
        assert job["company"] == "Acme Corp"
        assert job["url"].startswith(base_url)
        assert len(job["description"]) > 0


async def test_run_test_default_output_path(input_data, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    input_file = tmp_path / "input.json"

    async with run_mock_server(bind_host="127.0.0.1") as base_url:
        input_data["url"] = f"{base_url}/careers/"
        input_file = tmp_path / "input.json"
        input_file.write_text(json.dumps(input_data))

        config = TestConfig(input=str(input_file))
        await run_test(config)

    result = json.loads((tmp_path / "out.json").read_text())
    assert len(result) == len(ALL_JOBS)
