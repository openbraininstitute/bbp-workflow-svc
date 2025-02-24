"""Configuration for the auth service."""

from keycloak import KeycloakOpenID
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings for the auth service."""

    keycloak_server_url: str = Field(
        ...,
        env="KEYCLOAK_SERVER_URL",
        description="Keycloak host URL. Example: https://keycloak.example.com",
    )
    keycloak_realm: str = Field(
        ...,
        env="KEYCLOAK_REALM",
        description="Keycloak realm. Example: OBI",
    )
    keycloak_client_id: str = Field(
        ...,
        env="KEYCLOAK_CLIENT_ID",
        description="Keycloak client ID. Example: workflow-svc",
    )
    keycloak_client_secret: str = Field(
        ...,
        env="KEYCLOAK_CLIENT_SECRET",
        description="Keycloak client secret.",
    )
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


keycloak_openid = KeycloakOpenID(
    server_url=settings.keycloak_server_url,
    realm_name=settings.keycloak_realm,
    client_id=settings.keycloak_client_id,
    client_secret_key=settings.keycloak_client_secret,
)
