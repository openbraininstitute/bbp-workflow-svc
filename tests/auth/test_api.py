from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from auth.api import app


@pytest.fixture
def auth_client():
    """Create a test client for the auth service."""
    return TestClient(app)


@patch("auth.service.keycloak_openid.userinfo")
def test_store_refresh_token(
    mock_userinfo,
    auth_client,
    mock_access_token,
    mock_refresh_token,
    mock_userinfo_response_valid,
):
    """Test the store tokens endpoint."""

    mock_userinfo.return_value = mock_userinfo_response_valid

    response = auth_client.post(
        "/store-refresh-token",
        headers={"Authorization": f"Bearer {mock_access_token}"},
        json={"refresh-token": mock_refresh_token},
    )
    assert response.status_code == 200, response.text


@patch("auth.service.keycloak_openid.userinfo")
@patch("auth.service.keycloak_openid.refresh_token")
def test_refresh_token(
    mock_refreshtoken,
    mock_userinfo,
    auth_client,
    mock_access_token,
    mock_refresh_token,
    mock_userinfo_response_valid,
):
    """Test the refresh token endpoint."""
    mock_userinfo.return_value = mock_userinfo_response_valid
    mock_refreshtoken.return_value = {
        "access_token": mock_access_token,
        "refresh_token": mock_refresh_token,
        "expires_at": 1000,
        "subject_id": "test_subject_id",
    }

    response = auth_client.post(
        "/store-refresh-token",
        headers={"Authorization": f"Bearer {mock_access_token}"},
        json={"refresh-token": mock_refresh_token},
    )

    assert response.status_code == 200, response.text

    response = auth_client.get(
        "/refresh-token",
        headers={"Authorization": f"Bearer {mock_access_token}"},
    )
    assert response.status_code == 200


@patch("auth.service.keycloak_openid.userinfo")
def test_validate_token(
    mock_userinfo, auth_client, mock_access_token, mock_userinfo_response_valid
):
    """Test the validate token endpoint."""
    mock_userinfo.return_value = mock_userinfo_response_valid

    response = auth_client.get(
        "/validate-token",
        headers={"Authorization": f"Bearer {mock_access_token}"},
    )
    assert response.status_code == 200, response.text
