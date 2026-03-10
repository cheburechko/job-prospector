from dataclasses import dataclass, field


@dataclass
class CareersPageScenario:
    job_card_selector: str
    job_link_selector: str
    next_page_selector: str | None = None
    next_page_disabled_attr: str = ""
    next_page_disabled_value: str = ""

    def to_dict(self) -> dict:
        d = {
            "job_card_selector": self.job_card_selector,
            "job_link_selector": self.job_link_selector,
        }
        if self.next_page_selector is not None:
            d["next_page_selector"] = self.next_page_selector
            d["next_page_disabled_attr"] = self.next_page_disabled_attr
            d["next_page_disabled_value"] = self.next_page_disabled_value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "CareersPageScenario":
        return cls(
            job_card_selector=data["job_card_selector"],
            job_link_selector=data["job_link_selector"],
            next_page_selector=data.get("next_page_selector"),
            next_page_disabled_attr=data.get("next_page_disabled_attr", ""),
            next_page_disabled_value=data.get("next_page_disabled_value", ""),
        )


@dataclass
class JobPageScenario:
    title_selectors: list[str] = field(default_factory=list)
    location_selectors: list[str] = field(default_factory=list)
    description_selectors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title_selectors": self.title_selectors,
            "location_selectors": self.location_selectors,
            "description_selectors": self.description_selectors,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobPageScenario":
        return cls(
            title_selectors=data.get("title_selectors", []),
            location_selectors=data.get("location_selectors", []),
            description_selectors=data.get("description_selectors", []),
        )
