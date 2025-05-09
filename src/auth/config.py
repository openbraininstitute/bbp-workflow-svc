"""Configuration for the auth service."""

from typing import Annotated

from keycloak import KeycloakOpenID
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings for the auth service."""

    keycloak_server_url: str = Field(
        ...,
        alias="AUTH_KEYCLOAK_SERVER_URL",
        description="Keycloak host URL. Example: https://keycloak.example.com",
    )
    keycloak_realm: str = Field(
        ...,
        alias="AUTH_KEYCLOAK_REALM",
        description="Keycloak realm. Example: OBI",
    )
    keycloak_client_id: str = Field(
        ...,
        alias="AUTH_KEYCLOAK_CLIENT_ID",
        description="Keycloak client ID. Example: workflow-svc",
    )
    keycloak_client_secret: str = Field(
        ...,
        alias="AUTH_KEYCLOAK_CLIENT_SECRET",
        description="Keycloak client secret.",
    )
    redirect_uri: Annotated[
        str,
        Field(
            alias="AUTH_REDIRECT_URI",
            description="Redirect uri for keycloak after user authentication.",
        ),
    ]
    model_config = SettingsConfigDict(extra="ignore")


settings = Settings()


keycloak_openid = KeycloakOpenID(
    server_url=settings.keycloak_server_url,
    realm_name=settings.keycloak_realm,
    client_id=settings.keycloak_client_id,
    client_secret_key=settings.keycloak_client_secret,
)
