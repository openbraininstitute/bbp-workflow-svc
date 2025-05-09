"""Token management api client."""

from app.common import ProjectContext
from app.util import make_request


class AuthClient:
    """A client for the auth service."""

    def __init__(self, api_url: str, project_context: ProjectContext):
        """Initialize the auth client.

        Args:
            api_url: The URL of the auth service.
            project_context: The project context.
        """
        self.api_url = api_url
        self.project_context = project_context

    def register_tokens(self, *, access_token: str, refresh_token: str) -> None:
        """Register acces and refresh tokens in auth service.

        The tokens are stored in the auth service using the initial access token as key.

        Args:
            access_token: The access token.
            refresh_token: The refresh token.
        """
        _make_auth_request(
            url=f"{self.api_url}/store-refresh-token",
            method="POST",
            json={"refresh-token": refresh_token},
            project_context=self.project_context,
            token=access_token,
        )

    def refresh_token(self, *, access_token: str) -> str:
        """Refresh the access token.

        Args:
            access_token: The initial access token used to register the tokens.

        Returns:
            The new access token.
        """
        response = _make_auth_request(
            url=f"{self.api_url}/refresh-token",
            method="POST",
            project_context=self.project_context,
            token=access_token,
        )
        return response.json()["access-token"]

    def validate_token(self, *, access_token: str) -> None:
        """Validate the access token.

        Args:
            access_token: A valid access token.
        """
        _make_auth_request(
            url=f"{self.api_url}/validate-token",
            method="GET",
            project_context=self.project_context,
            token=access_token,
        )


def _make_auth_request(
    *,
    url: str,
    method: str,
    project_context: ProjectContext,
    json: dict | None = None,
    token: str,
):
    """Make an auth request."""
    return make_request(
        url=url,
        method=method,
        headers={
            "project-id": project_context.project_id,
            "virtual-lab-id": project_context.virtual_lab_id,
            "Authorization": f"Bearer {token}",
        },
        json=json,
        timeout=10,
    )
