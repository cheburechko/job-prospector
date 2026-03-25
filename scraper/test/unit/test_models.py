from models.company import Company
from models.scenario import CareersPageScenario, JobPageScenario
from test.helpers import make_company_json


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


class TestCompany:
    def test_from_json_without_rps(self):
        data = make_company_json()
        company = Company.from_dict(data)
        assert company.company == "Acme"
        assert company.rps is None

    def test_from_json_with_rps(self):
        data = make_company_json(rps=5.0)
        company = Company.from_dict(data)
        assert company.rps == 5.0


class TestJobPageScenario:
    def test_round_trip(self):
        scenario = JobPageScenario(
            title_selectors=["h1", 'meta[property="og:title"]'],
            location_selectors=[".location"],
            description_selectors=[".desc"],
        )
        data = scenario.to_dict()
        restored = JobPageScenario.from_dict(data)
        assert restored.title_selectors == scenario.title_selectors
        assert restored.location_selectors == scenario.location_selectors
        assert restored.description_selectors == scenario.description_selectors
