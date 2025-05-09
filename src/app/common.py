"""Common stuff."""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class ProjectContext:
    """Project context dataclass."""

    virtual_lab_id: UUID
    project_id: UUID
