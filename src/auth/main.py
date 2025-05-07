"""Main module for the auth service."""

from typing import Annotated

from fastapi import Body, Depends, FastAPI, Header, HTTPException
from fastapi.requests import Request
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer

from auth import service
from auth.config import keycloak_openid, settings
from auth.logger import L
from auth.models import (
    ProjectContext,
    StoreRefreshTokenBody,
    TokenInfo,
    TokenPair,
    TokenPairInput,
    TokenResponse,
)
from auth.storage import TokenStorage

app = FastAPI()
http_bearer_scheme = HTTPBearer()

TOKEN_STORAGE = TokenStorage()


def _extract_token(authorization: str = Header(...)) -> str:
    """Return the access token from the Authorization header."""
    if not authorization.startswith("Bearer "):
        L.error("Invalid Authorization header format")
        raise HTTPException(
            status_code=400,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'.",
        )
    return authorization.removeprefix("Bearer ")


def _extract_project_context(
    virtual_lab_id: str | None = Header(default=None),
    project_id: str | None = Header(default=None),
) -> ProjectContext:
    """Returb the project context from the header if any."""
    if virtual_lab_id is None and project_id is None:
        L.warning("No project context provided.")
        return None
    return ProjectContext(virtual_lab_id=virtual_lab_id, project_id=project_id)


@app.get("/health", tags=["Health"])
async def health_check():
    """Make health check."""
    return {"status": "ok"}


@app.get("/login")
def login(request: Request):
    """Redirect user to keycloak login and then call register-token-pair endpoint.

    Use the authorization code flow to redirect a user to login, produce a code,
    which is then used by the workflow to produce the token pair.
    """
    # Generate the authentication URL to redirect the user to Keycloak's login page.
    auth_url = keycloak_openid.auth_url(redirect_uri=settings.redirect_uri)
    L.info("User will be redirected to keycloak's login page.")
    L.info("Redirect uri %s", settings.redirect_uri)
    return RedirectResponse(auth_url)


@app.get("/register-token-pair")
def register_token_pair(request: Request):
    code = request.query_params.get("code")

    if not code:
        raise HTTPException(status_code=400, detail="Missing code parameter in request.")

    try:
        # Exchange the authorization code for tokens
        token_response = keycloak_openid.token(redirect_uri=settings.redirect_uri, code=code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {str(e)}")

    token_info = service.validate_token_pair(
        token_pair=token_pair_input,
        project_context=project_context,
    )
    token_pair = TokenPair(
        access_token=token_pair_input.access_token,
        refresh_token=token_pair_input.refresh_token,
        expires_at=token_info.expires_at,
        subject_id=token_info.subject_id,
    )
    # store the pair in the storage using the initial access token as key.
    TOKEN_STORAGE.add_token_pair(token_pair)
    return {"message": "Tokens stored successfully"}


@app.post("/store-refresh-token")
def store_refresh_token(
    body: Annotated[StoreRefreshTokenBody, Body()],
    access_token: Annotated[str, Depends(_extract_token)],
    project_context: Annotated[ProjectContext | None, Depends(_extract_project_context)],
):
    """Store a refresh token."""
    token_pair_input = TokenPairInput(
        access_token=access_token,
        refresh_token=body.refresh_token,
    )
    token_info = service.validate_token_pair(
        token_pair=token_pair_input,
        project_context=project_context,
    )
    token_pair = TokenPair(
        access_token=token_pair_input.access_token,
        refresh_token=token_pair_input.refresh_token,
        expires_at=token_info.expires_at,
        subject_id=token_info.subject_id,
    )
    # store the pair in the storage using the initial access token as key.
    TOKEN_STORAGE.add_token_pair(token_pair)
    L.info("Tokens stored successfully for subject %s", token_info.subject_id)
    return {"message": "Tokens stored successfully"}


@app.get("/refresh-token")
def refresh_token(
    storage_key: Annotated[str, Depends(_extract_token)],
    project_context: Annotated[ProjectContext | None, Depends(_extract_project_context)],
) -> TokenResponse:
    """Refresh the access token."""
    try:
        token_pair = TOKEN_STORAGE.get_token_pair(storage_key)
    except KeyError:
        raise HTTPException(status_code=404, detail="Access token not found") from None

    new_token_pair = service.refresh_token_pair(token_pair)

    TOKEN_STORAGE.update_token_pair(storage_key, new_token_pair)
    L.info("Tokens refreshed successfully for subject %s", token_pair.subject_id)
    return TokenResponse(
        access_token=new_token_pair.access_token,
    )


@app.get("/validate-token")
def validate_token(
    access_token: Annotated[str, Depends(_extract_token)],
    project_context: Annotated[ProjectContext | None, Depends(_extract_project_context)],
) -> TokenInfo:
    """Validate access token.

    Validation is done by checking if the access token:
        - has expired
        - has valid user credentials
        - is consistent with the project context
    """
    return service.validate_access_token(
        token=access_token,
        project_context=project_context,
    )
