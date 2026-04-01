from test.helpers import make_job


class TestCompanyBatchWriter:
    async def test_add(self, dynamodb_storage, company):
        async with dynamodb_storage.company_writer() as writer:
            await writer.add(company)

        companies = await dynamodb_storage.load_companies()
        assert companies == [company]

    async def test_delete(self, dynamodb_storage, company):
        async with dynamodb_storage.company_writer() as writer:
            await writer.add(company)

        async with dynamodb_storage.company_writer() as writer:
            await writer.delete(company.company)

        companies = await dynamodb_storage.load_companies()
        assert len(companies) == 0


class TestJobBatchWriter:
    async def test_add(self, dynamodb_storage):
        job = make_job()
        async with dynamodb_storage.job_writer() as writer:
            await writer.add(job)

        jobs = await dynamodb_storage.list_jobs(job.company)
        assert jobs == [job]

    async def test_delete(self, dynamodb_storage):
        async with dynamodb_storage.job_writer() as writer:
            await writer.add(make_job())

        async with dynamodb_storage.job_writer() as writer:
            await writer.delete("Acme", "https://example.com/jobs/1")

        jobs = await dynamodb_storage.list_jobs("Acme")
        assert len(jobs) == 0


class TestDynamoDbStorage:
    async def test_load_companies(self, dynamodb_storage, company):
        async with dynamodb_storage.company_writer() as writer:
            await writer.add(company)

        companies = await dynamodb_storage.load_companies()
        assert companies == [company]

    async def test_list_jobs(self, dynamodb_storage):
        job1 = make_job(company="Acme")
        job2 = make_job(company="Other", url="https://other.com/1")
        async with dynamodb_storage.job_writer() as writer:
            await writer.add(job1)
            await writer.add(job2)

        jobs = await dynamodb_storage.list_jobs(job1.company)
        assert jobs == [job1]

    async def test_list_job_urls(self, dynamodb_storage):
        job1 = make_job(company="Acme", url="https://example.com/jobs/1")
        job2 = make_job(company="Acme", url="https://example.com/jobs/2")
        job3 = make_job(company="Other", url="https://other.com/1")
        async with dynamodb_storage.job_writer() as writer:
            await writer.add(job1)
            await writer.add(job2)
            await writer.add(job3)

        urls = await dynamodb_storage.list_job_urls("Acme")
        assert urls == {"https://example.com/jobs/1", "https://example.com/jobs/2"}
