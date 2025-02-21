"""entitycore client for bbp-workflow-svc."""

import io
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, TypeAdapter

from app.common import ProjectContext
from app.environment import DB_API_URL
from app.util import make_request


class Asset(BaseModel):
    """Asset is a file uploaded to entitycore."""

    id: int | None = None
    path: str
    fullpath: str
    bucket_name: str
    is_directory: bool
    content_type: str
    size: int
    meta: dict


@dataclass
class FileToUpload:
    """FileToUpload is a file to be uploaded to entitycore."""

    filename: str
    content_type: str
    buffer_or_path: str | io.BytesIO


class Entity(BaseModel):
    """Entity base model."""

    id: int | None = None
    name: str | None = None
    description: str | None = None
    assets: list[Asset] | None = None

    creation_date: datetime | None = None
    update_date: datetime | None = None

    __route__: ClassVar[str] = "entity"

    @property
    def url(self):
        """Return entity url."""
        return f"{DB_API_URL}/{self.__route__}/{self.id}" if self.id else None


class WorkflowExecution(Entity):
    """WorkflowExecution base model."""

    module: str
    task: str
    version: str
    configFileName: str
    status: str
    startedAtTime: datetime
    endedAtTime: datetime | None = None

    __route__: ClassVar[str] = "workflow_execution"


def upload_files(
    *,
    resource_id: int,
    resource_type: str,
    project_context: ProjectContext,
    files_to_upload: list[FileToUpload],
    token: str,
):
    """Upload files via entitycore api."""
    assets = []
    for f in files_to_upload:
        data = {"file": (f.filename, f.buffer_or_path, f.content_type)}

        response = make_request(
            method="POST",
            url=f"{DB_API_URL}/{resource_type}/{resource_id}/assets",
            files=data,
            headers={
                "project-id": project_context.project_id,
                "virtual-lab-id": project_context.virtual_lab_id,
                "Authorization": f"Bearer {token}",
            },
        )

        asset = Asset.model_validate(response.json())
        assets.append(asset)
    return assets


def get_entity(resource_id: int, *, model: Entity, project_context: ProjectContext, token: str):
    """Get entity via entitycore api."""
    url = f"{DB_API_URL}/{model.__route__}/{resource_id}"

    response = make_request(
        method="GET",
        url=url,
        headers={
            "project-id": project_context.project_id,
            "virtual-lab-id": project_context.virtual_lab_id,
            "Authorization": f"Bearer {token}",
        },
    )

    json_data = response.json()

    # if model.assets:
    #    raise NotImplementedError("Distribution is not supported")

    return model.model_validate(json_data)


def update_entity(
    resource_id: int,
    *,
    model: Entity,
    project_context: ProjectContext,
    token: str,
    attributes_to_update,
    # model_with_updates,
):
    """Update entity via entitycore api."""
    url = f"{DB_API_URL}/{model.__route__}/{resource_id}"

    json_data = TypeAdapter(dict).dump_python(attributes_to_update, mode="json")

    response = make_request(
        method="PATCH",
        url=url,
        headers={
            "project-id": project_context.project_id,
            "virtual-lab-id": project_context.virtual_lab_id,
            "Authorization": f"Bearer {token}",
        },
        json=json_data,
    )

    json_data = response.json()

    # if model.assets:
    #    raise NotImplementedError("Distribution is not supported")

    return model.model_validate(json_data)


def register_entity(
    entity: Entity,
    files_to_upload: list[FileToUpload],
    project_context: ProjectContext,
    token: str,
):
    """Register entity via entitycore api."""
    json_data = entity.model_dump(mode="json", exclude_none=True)

    # TODO: Improve files_to_upload and assets

    response = make_request(
        method="POST",
        url=f"{DB_API_URL}/{entity.__route__}/",
        headers={
            "project-id": project_context.project_id,
            "virtual-lab-id": project_context.virtual_lab_id,
            "Authorization": f"Bearer {token}",
        },
        json=json_data,
    )

    json_data = response.json()

    entity_id = json_data["id"]

    assets = None
    if files_to_upload:
        assets = upload_files(
            resource_id=entity_id,
            resource_type=entity.__route__,
            project_context=project_context,
            files_to_upload=files_to_upload,
            token=token,
        )

    # instantiate with updated entries from response
    return entity.__class__.model_validate(response.json() | {"assets": assets})


def _test_register_entity():

    project_id = "ee86d4a0-eaca-48ca-9788-ddc450250b15"
    virtual_lab_id = "9c6fba01-2c6f-4eac-893f-f0dc665605c5"

    project_context = ProjectContext(project_id=project_id, virtual_lab_id=virtual_lab_id)

    with tempfile.TemporaryDirectory() as temp_dir:

        f1_path = Path(temp_dir) / "f1.txt"
        f1_path.write_text("foo")

        f2_buffer = io.BytesIO(b"bar").getvalue()

        files = [
            FileToUpload(filename="foo", content_type="text/plain", buffer_or_path=str(f1_path)),
            FileToUpload(filename="bar", content_type="text/plain", buffer_or_path=f2_buffer),
        ]

        w = WorkflowExecution(
            name="foo",
            description="bar",
            module="mod",
            task="task",
            version="ver",
            configFileName="cfg",
            id=None,
            status="Running",
            startedAtTime=datetime.utcnow(),
        )

        res1 = register_entity(
            entity=w,
            project_context=project_context,
            token="token",
            files_to_upload=files,
        )

        res2 = update_entity(
            resource_id=res1.id,
            model=WorkflowExecution,
            project_context=project_context,
            token="token",
            attributes_to_update={
                "status": "Completed",
                "endedAtTime": datetime.utcnow(),
            },
        )

        assert res1.id == res2.id

        res3 = get_entity(
            resource_id=res1.id,
            model=WorkflowExecution,
            project_context=project_context,
            token="token",
        )
        print(res3)
