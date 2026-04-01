import asyncio
from test.helpers import make_company


class TestSqsQueue:
    async def test_receive_messages(self, sqs_queue, company):
        await sqs_queue.client.send_message(
            QueueUrl=sqs_queue.config.queue_url,
            MessageBody=company.to_json(),
        )

        messages = await sqs_queue.receive_messages()
        assert len(messages) == 1
        assert messages[0].company == company
        assert messages[0].receipt_handle

    async def test_receive_messages_empty(self, sqs_queue):
        messages = await sqs_queue.receive_messages()
        assert messages == []

    async def test_delete_message(self, sqs_queue, company):
        await sqs_queue.client.send_message(
            QueueUrl=sqs_queue.config.queue_url,
            MessageBody=company.to_json(),
        )

        messages = await sqs_queue.receive_messages()
        await sqs_queue.delete_message(messages[0].receipt_handle)

        remaining = await sqs_queue.receive_messages()
        assert remaining == []

    async def test_send_message(self, sqs_queue, company):
        await sqs_queue.send_message(company)

        messages = await sqs_queue.receive_messages()
        assert len(messages) == 1
        assert messages[0].company == company

    async def test_extend_message_visibility(self, sqs_queue, company):
        await sqs_queue.send_message(company)
        messages = await sqs_queue.receive_messages()
        assert len(messages) == 1
        messages[0].stop_heartbeat()

        for _ in range(4):
            await asyncio.sleep(await sqs_queue.get_visibility_timeout() / 2)
            assert [] == await sqs_queue.receive_messages()
            await sqs_queue.extend_message_visibility_timeout(
                messages[0].receipt_handle
            )

    async def test_receive_multiple_messages(self, sqs_queue, company):
        other = make_company(company="Other", url="https://other.com/jobs")

        await sqs_queue.client.send_message(
            QueueUrl=sqs_queue.config.queue_url,
            MessageBody=company.to_json(),
        )
        await sqs_queue.client.send_message(
            QueueUrl=sqs_queue.config.queue_url,
            MessageBody=other.to_json(),
        )

        messages = await sqs_queue.receive_messages()
        assert len(messages) == 2
        companies = {msg.company.company for msg in messages}
        assert companies == {"Acme", "Other"}
