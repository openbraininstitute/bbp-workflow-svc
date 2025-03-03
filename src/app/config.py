"""Configuration for the workflow service."""

from pathlib import Path
from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.auth import AuthClient
from app.common import ProjectContext


def _path_exists(path: Path) -> Path:
    """Check if a path exists."""
    if not path.exists():
        raise ValueError(f"The path {path} does not exist.")
    return path


class Settings(BaseSettings):
    """Settings for the auth service."""

    app_name: str = Field(
        ...,
        env="APP_NAME",
        description="The name of this application",
    )
    app_version: str = Field(..., env="APP_VERSION", description="The version of this application.")
    auth_api_url: str = Field(
        ...,
        env="AUTH_API_URL",
        description="The API URL of the auth sidecar service for token management.",
    )
    commit_sha: str = Field(
        ..., env="COMMIT_SHA", description="The commit SHA that was used to build the application."
    )
    db_api_url: str = Field(
        ...,
        env="DB_API_URL",
        description="The API URL of the database service (entitycore).",
    )
    debug: bool = Field(
        default=False,
        env="DEBUG",
        description="Whether to run in debug mode.",
    )
    hpc_resource_provisioner_api_url: str = Field(
        ...,
        env="HPC_RESOURCE_PROVISIONER_API_URL",
        description="The API URL of the HPC resource provisioner service.",
    )
    project_id: str = Field(
        env="PROJECT_ID",
        description="The project id with which the service is associated.",
    )
    virtual_lab_id: str = Field(
        ...,
        env="VIRTUAL_LAB_ID",
        description="The virtual lab id with which the service is associated.",
    )
    workflows_path: Path = Field(
        default=Path("."),
        env="WORKFLOWS_PATH",
        description="The path to the workflows directory within the container.",
    )
    luigi_cfg_path: Annotated[Path, _path_exists] = Field(
        default=Path("/etc/luigi/luigi.cfg"),
        env="LUIGI_CFG_PATH",
        description="The path to the Luigi configuration file within the container.",
    )
    logging_cfg_path: Annotated[Path, _path_exists] = Field(
        default=Path("/code/logging.cfg"),
        env="LOGGING_CFG_PATH",
        description="The path to the logging configuration file within the container.",
    )
    idle_timeout: int = Field(
        default=30 * 60,
        env="IDLE_TIMEOUT",
        description="The idle timeout for the workflow service in seconds.",
    )
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# each instance is associated with one vlab/proj
INSTANCE_PROJECT_CONTEXT = ProjectContext(
    virtual_lab_id=settings.virtual_lab_id,
    project_id=settings.project_id,
)

# Authentication client to use for token management
auth_client = AuthClient(api_url=settings.auth_api_url, project_context=INSTANCE_PROJECT_CONTEXT)
