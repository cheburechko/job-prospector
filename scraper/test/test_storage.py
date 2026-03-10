import json

from scraper.models.job import Job
from scraper.storage.json_storage import JsonStorage


class TestJsonStorage:
    def test_load_site_configs(self, tmp_path):
        site_data = {
            "company": "Acme",
            "url": "https://example.com/jobs",
            "careers_page": {
                "job_card_selector": "div.job",
                "job_link_selector": "a",
            },
            "job_page": {
                "title_selectors": ["h1"],
                "location_selectors": [".loc"],
                "description_selectors": [".desc"],
            },
        }
        (tmp_path / "acme.json").write_text(json.dumps(site_data))

        storage = JsonStorage(sites_dir=str(tmp_path), output_path="unused")
        configs = storage.load_site_configs()
        assert len(configs) == 1
        assert configs[0].company == "Acme"

    def test_save_jobs(self, tmp_path):
        output_path = str(tmp_path / "results.json")
        storage = JsonStorage(sites_dir="unused", output_path=output_path)

        jobs = [
            Job(company="Acme", title="Engineer", location="Remote", description="Build things"),
            Job(company="Acme", title="Designer", location="Berlin", description="Design things"),
        ]
        storage.save_jobs(jobs)

        saved = json.loads((tmp_path / "results.json").read_text())
        assert len(saved) == 2
        assert saved[0]["title"] == "Engineer"
        assert saved[1]["location"] == "Berlin"
