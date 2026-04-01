from commands.scheduler import run
from test.helpers import make_company


class TestScheduler:
    async def test_sends_companies_to_queue(self, dynamodb_storage, sqs_queue):
        company1 = make_company(company="Acme", url="https://acme.com/jobs")
        company2 = make_company(company="Other", url="https://other.com/jobs")
        async with dynamodb_storage.company_writer() as writer:
            await writer.add(company1)
            await writer.add(company2)

        await run(dynamodb_storage, sqs_queue)

        messages = await sqs_queue.receive_messages()
        assert {msg.company.company for msg in messages} == {"Acme", "Other"}

    async def test_no_companies(self, dynamodb_storage, sqs_queue):
        await run(dynamodb_storage, sqs_queue)

        messages = await sqs_queue.receive_messages()
        assert messages == []
