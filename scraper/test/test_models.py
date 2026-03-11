import json

from models.scenario import CareersPageScenario, JobPageScenario
from storage.json_storage import JsonStorage


class TestCareersPageScenario:
    def test_round_trip(self):
        scenario = CareersPageScenario(
            job_card_selector="tr.job-post",
            job_link_selector="a",
            next_page_selector="button.next",
            next_page_disabled_attr="aria-disabled",
            next_page_disabled_value="true",
        )
        data = scenario.to_dict()
        restored = CareersPageScenario.from_dict(data)
        assert restored.job_card_selector == scenario.job_card_selector
        assert restored.job_link_selector == scenario.job_link_selector
        assert restored.next_page_selector == scenario.next_page_selector
        assert restored.next_page_disabled_attr == scenario.next_page_disabled_attr
        assert restored.next_page_disabled_value == scenario.next_page_disabled_value

    def test_round_trip_no_pagination(self):
        scenario = CareersPageScenario(
            job_card_selector="div.job",
            job_link_selector="a.link",
        )
        data = scenario.to_dict()
        assert data["next_page_selector"] is None
        restored = CareersPageScenario.from_dict(data)
        assert restored.next_page_selector is None


class TestSiteConfig:
    def _make_site_json(self, tmp_path, **extra):
        data = {
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
            **extra,
        }
        path = tmp_path / "acme.json"
        path.write_text(json.dumps(data))
        return tmp_path

    def test_load_without_rps(self, tmp_path):
        d = self._make_site_json(tmp_path)
        storage = JsonStorage(sites_dir=str(d), output_path="unused")
        sites = storage.load_site_configs()
        assert len(sites) == 1
        assert sites[0].company == "Acme"
        assert sites[0].rps is None

    def test_load_with_rps(self, tmp_path):
        d = self._make_site_json(tmp_path, rps=5.0)
        storage = JsonStorage(sites_dir=str(d), output_path="unused")
        sites = storage.load_site_configs()
        assert sites[0].rps == 5.0


class TestJobPageScenario:
    def test_round_trip(self):
        scenario = JobPageScenario(
            title_selectors=["h1", "meta[property=\"og:title\"]"],
            location_selectors=[".location"],
            description_selectors=[".desc"],
        )
        data = scenario.to_dict()
        restored = JobPageScenario.from_dict(data)
        assert restored.title_selectors == scenario.title_selectors
        assert restored.location_selectors == scenario.location_selectors
        assert restored.description_selectors == scenario.description_selectors
