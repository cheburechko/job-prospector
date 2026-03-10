from scraper.models.scenario import CareersPageScenario, JobPageScenario


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
        assert "next_page_selector" not in data
        restored = CareersPageScenario.from_dict(data)
        assert restored.next_page_selector is None


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
