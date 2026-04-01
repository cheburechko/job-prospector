import json

import pytest

from commands.scrape_one import ScrapeOneConfig, run_scrape_one
from models.company import Company
from test.conftest import ALL_JOBS, run_mock_server

pytestmark = pytest.mark.asyncio


@pytest.fixture
def input_data(fixtures_dir):
    data = json.loads(fixtures_dir.joinpath("site.json").read_text())
    data["url"] = "PLACEHOLDER"
    return data


async def test_scrape_one_from_file(input_data, tmp_path):
    output_file = tmp_path / "out.json"
    input_file = tmp_path / "input.json"

    async with run_mock_server(bind_host="127.0.0.1") as base_url:
        input_data["url"] = f"{base_url}/careers/"
        input_file.write_text(json.dumps(input_data))

        config = ScrapeOneConfig(input=str(input_file), output=str(output_file))
        await run_scrape_one(config)

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


async def test_scrape_one_from_dynamodb(dynamodb_storage, input_data, tmp_path):
    output_file = tmp_path / "out.json"

    async with run_mock_server(bind_host="127.0.0.1") as base_url:
        input_data["url"] = f"{base_url}/careers/"
        company = Company.from_dict(input_data)
        async with dynamodb_storage.company_writer() as writer:
            await writer.add(company)

        config = ScrapeOneConfig(
            company="Acme Corp",
            output=str(output_file),
            dynamodb=dynamodb_storage.config,
        )
        await run_scrape_one(config)

    result = json.loads(output_file.read_text())
    assert len(result) == len(ALL_JOBS)

    titles = {job["title"] for job in result}
    assert titles == {j["title"] for j in ALL_JOBS}


async def test_scrape_one_default_output_path(input_data, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    input_file = tmp_path / "input.json"

    async with run_mock_server(bind_host="127.0.0.1") as base_url:
        input_data["url"] = f"{base_url}/careers/"
        input_file = tmp_path / "input.json"
        input_file.write_text(json.dumps(input_data))

        config = ScrapeOneConfig(input=str(input_file))
        await run_scrape_one(config)

    result = json.loads((tmp_path / "out.json").read_text())
    assert len(result) == len(ALL_JOBS)


async def test_scrape_one_company_not_found(dynamodb_storage, tmp_path):
    config = ScrapeOneConfig(
        company="NonExistent",
        output=str(tmp_path / "out.json"),
        dynamodb=dynamodb_storage.config,
    )
    with pytest.raises(ValueError, match="Company 'NonExistent' not found"):
        await run_scrape_one(config)


async def test_scrape_one_no_input_or_company():
    config = ScrapeOneConfig(output="out.json")
    with pytest.raises(
        ValueError, match="Either --input or --company must be provided"
    ):
        await run_scrape_one(config)
