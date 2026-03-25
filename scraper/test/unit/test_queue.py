import pytest
from moto import mock_aws

from models.company import Company
from models.config import SqsConfig
from models.scenario import CareersPageScenario, JobPageScenario
from queues.sqs_queue import SqsQueue

REGION = "eu-central-1"
QUEUE_NAME = "test-scraper-queue"


@pytest.fixture
def sqs_queue():
    with mock_aws():
        import boto3

        client = boto3.client("sqs", region_name=REGION)
        response = client.create_queue(QueueName=QUEUE_NAME)
        queue_url = response["QueueUrl"]

        queue = SqsQueue(
            SqsConfig(
                queue_url=queue_url,
                region=REGION,
                wait_time_seconds=0,
                max_messages=10,
            )
        )
        yield queue


class TestSqsQueue:
    async def test_receive_messages(self, sqs_queue, company):
        sqs_queue.client.send_message(
            QueueUrl=sqs_queue.queue_url,
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
        sqs_queue.client.send_message(
            QueueUrl=sqs_queue.queue_url,
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

    async def test_receive_multiple_messages(self, sqs_queue, company):
        other = Company(
            company="Other",
            url="https://other.com/jobs",
            careers_page=CareersPageScenario(
                job_card_selector="div.job",
                job_link_selector="a",
            ),
            job_page=JobPageScenario(
                title_selectors=["h1"],
                location_selectors=[".loc"],
                description_selectors=[".desc"],
            ),
        )

        sqs_queue.client.send_message(
            QueueUrl=sqs_queue.queue_url,
            MessageBody=company.to_json(),
        )
        sqs_queue.client.send_message(
            QueueUrl=sqs_queue.queue_url,
            MessageBody=other.to_json(),
        )

        messages = await sqs_queue.receive_messages()
        assert len(messages) == 2
        companies = {msg.company.company for msg in messages}
        assert companies == {"Acme", "Other"}
