import pytest

from commands.schedule_one import ScheduleOne
from test.helpers import make_company

pytestmark = pytest.mark.asyncio


async def test_schedule_one(dynamodb_storage, sqs_queue):
    company = make_company(company="Acme", url="https://acme.com/jobs")
    async with dynamodb_storage.company_writer() as writer:
        await writer.add(company)

    config = ScheduleOne(
        company="Acme",
        dynamodb=dynamodb_storage.config,
        sqs=sqs_queue.config,
    )
    await config.cli_cmd()

    messages = await sqs_queue.receive_messages()
    assert len(messages) == 1
    assert messages[0].company == company


async def test_schedule_one_company_not_found(dynamodb_storage, sqs_queue):
    config = ScheduleOne(
        company="NonExistent",
        dynamodb=dynamodb_storage.config,
        sqs=sqs_queue.config,
    )
    with pytest.raises(ValueError, match="Company 'NonExistent' not found"):
        await config.cli_cmd()
