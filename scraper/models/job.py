from dataclasses import dataclass


@dataclass
class Job:
    company: str
    title: str
    location: str
    description: str
