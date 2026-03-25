from test.helpers import make_job


class TestDynamoDbStorage:
    async def test_load_companies(self, dynamodb_storage, company):
        await dynamodb_storage.add_company(company)
        companies = await dynamodb_storage.load_companies()
        assert companies == [company]

    async def test_add_company(self, dynamodb_storage, company):
        await dynamodb_storage.add_company(company)

        companies = await dynamodb_storage.load_companies()
        assert companies == [company]

    async def test_delete_company(self, dynamodb_storage, company):
        await dynamodb_storage.add_company(company)
        await dynamodb_storage.delete_company(company.company)

        companies = await dynamodb_storage.load_companies()
        assert len(companies) == 0

    async def test_add_job(self, dynamodb_storage):
        job = make_job()
        await dynamodb_storage.add_job(job)

        jobs = await dynamodb_storage.list_jobs(job.company)
        assert jobs == [job]

    async def test_delete_job(self, dynamodb_storage):
        await dynamodb_storage.add_job(make_job())
        await dynamodb_storage.delete_job("Acme", "https://example.com/jobs/1")

        jobs = await dynamodb_storage.list_jobs("Acme")
        assert len(jobs) == 0

    async def test_list_jobs(self, dynamodb_storage):
        job1 = make_job(company="Acme")
        job2 = make_job(company="Other", url="https://other.com/1")
        await dynamodb_storage.add_job(job1)
        await dynamodb_storage.add_job(job2)

        jobs = await dynamodb_storage.list_jobs(job1.company)
        assert jobs == [job1]
