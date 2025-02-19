"""Common stuff."""

from dataclasses import dataclass


@dataclass
class ProjectContext:
    """Project context dataclass."""

    virtual_lab_id: str
    project_id: str
