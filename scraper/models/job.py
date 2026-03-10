from dataclasses import dataclass

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class Job:
    company: str
    title: str
    location: str
    description: str
