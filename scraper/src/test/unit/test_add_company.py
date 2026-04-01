import json

import pytest

from commands.add_company import AddCompanyConfig, run_add_company
from test.helpers import make_company, make_company_json

pytestmark = pytest.mark.asyncio


async def test_run_add_company(dynamodb_storage, tmp_path):
    input_file = tmp_path / "company.json"
    input_file.write_text(json.dumps(make_company_json()))

    config = AddCompanyConfig(
        input=str(input_file),
        dynamodb=dynamodb_storage.config,
    )
    await run_add_company(config)

    companies = await dynamodb_storage.load_companies()
    assert companies == [make_company()]
