from dataclasses import dataclass, field

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class CareersPageScenario:
    job_card_selector: str
    job_link_selector: str
    next_page_selector: str | None = None
    next_page_disabled_attr: str = ""
    next_page_disabled_value: str = ""


@dataclass_json
@dataclass
class JobPageScenario:
    title_selectors: list[str] = field(default_factory=list)
    location_selectors: list[str] = field(default_factory=list)
    description_selectors: list[str] = field(default_factory=list)
