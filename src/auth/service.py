"""Authentication service."""

from fastapi import HTTPException, status
from keycloak.exceptions import KeycloakAuthenticationError

from auth.config import keycloak_openid
from auth.logger import L
from auth.models import ProjectContext, TokenInfo, TokenPair, TokenPairInput, UserInfo
from auth.util import get_timestamp_now


def authenticate_user(username: str, password: str) -> str:
    """Authenticate the user using Keycloak and return an access token.

    Args:
        username: The username of the user.
        password: The password of the user.

    Returns:
        The access token of the user.
    """
    try:
        token = keycloak_openid.token(username, password)
        return token["access_token"]
    except KeycloakAuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        ) from e


def get_token_info(token: str) -> TokenInfo:
    """Get the token info."""
    info: dict = keycloak_openid.decode_token(token, validate=False)
    return TokenInfo(
        token=token,
        expires_at=info.get("exp", None),
        subject_id=info["sub"],
    )


def get_user_info(token: str) -> UserInfo:
    """Get the user info."""
    info: dict | bytes = keycloak_openid.userinfo(token)

    # userinfo returns an html page in bytes when authentication fails
    # TODO: Consider using the endpoint directly instead of userinfo method
    if isinstance(info, bytes):
        message = "Failed to validate user credentials."
        L.error(message)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message,
        ) from e

    user_info = UserInfo(
        subject_id=info["sub"],
        groups=info.get("groups", []),
    )

    L.info("Successfully retrieved user info for subject %s", user_info.subject_id)
    return user_info


def validate_access_token(token: str, project_context: ProjectContext | None = None) -> TokenInfo:
    """Validate the access token."""
    token_info = get_token_info(token)
    _validate_token_expiration_date(token_info)

    user_info = get_user_info(token)
    _validate_user_groups(user_info, project_context)

    L.info("Token validated successfully for subject %s", user_info.subject_id)
    return token_info


def _validate_token_expiration_date(token_info):
    """Validate that toke has not been expired."""
    now = get_timestamp_now()
    if token_info.expires_at < now:
        message = f"Access token has expired.\nExpiration date: {token_info.expires_at}\nNow: {now}"
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)


def _validate_user_groups(user_info, project_context: ProjectContext | None) -> None:
    """Validate that project context vlab/proj is in user groups."""
    if project_context and not _context_in_groups(project_context, user_info.groups):
        message = (
            "Access token groups are not consistent with the project context.\n"
            f"Project Context: {project_context}\n"
            f"Subject ID     : {user_info.subject_id}\n"
            f"User groups    : {user_info.groups}"
        )
        L.error(message)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)


def _context_in_groups(context: ProjectContext, groups: list[str]) -> bool:
    """Check if the context is in the groups."""
    proj_ids = {g.split("/")[2] for g in groups if g.startswith(("/proj"))}
    vlab_ids = {g.split("/")[2] for g in groups if g.startswith(("/vlab"))}
    return str(context.virtual_lab_id) in vlab_ids and str(context.project_id) in proj_ids


def validate_token_pair(
    token_pair: TokenPairInput, project_context: ProjectContext | None = None
) -> TokenPair:
    """Validate the token pair."""
    access_token_info = validate_access_token(
        token=token_pair.access_token, project_context=project_context
    )

    refresh_token_info = get_token_info(token_pair.refresh_token)

    if access_token_info.subject_id != refresh_token_info.subject_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token and refresh token subject IDs do not match.",
        )

    return TokenPair(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        expires_at=access_token_info.expires_at,
        subject_id=access_token_info.subject_id,
    )


def refresh_token_pair(token_pair: TokenPair) -> TokenPair:
    """Refresh the access token."""
    # TODO: check if access token is still valid within a margin of 1 minute

    data = keycloak_openid.refresh_token(token_pair.refresh_token)

    access_token = data["access_token"]
    token_info = get_token_info(access_token)

    return TokenPair(
        access_token=access_token,
        refresh_token=data["refresh_token"],
        expires_at=token_info.expires_at,
        subject_id=token_info.subject_id,
    )
