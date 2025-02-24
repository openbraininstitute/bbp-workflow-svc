"""Models for the auth service."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuthModel(BaseModel):
    """Base model for auth models."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )


class TokenPairInput(AuthModel):
    """A pair of access and refresh tokens."""

    access_token: str
    refresh_token: str


class TokenPair(TokenPairInput):
    """A pair of access and refresh tokens with token info."""

    expires_at: int
    subject_id: str


class TokenResponse(AuthModel):
    """A response containing an access token."""

    access_token: str


class UserInfo(AuthModel):
    """User information."""

    subject_id: str
    groups: list[str]


class TokenInfo(AuthModel):
    """Token information."""

    expires_at: int | None
    subject_id: str


class ProjectContext(AuthModel):
    """A project context."""

    virtual_lab_id: UUID
    project_id: UUID


class StoreRefreshTokenBody(BaseModel):
    """A body for storing a refresh token."""

    refresh_token: str = Field(..., alias="refresh-token")
