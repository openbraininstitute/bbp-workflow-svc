from unittest.mock import patch

import pytest
from fastapi import HTTPException
from keycloak.exceptions import KeycloakAuthenticationError

from auth import service as test_module
from auth.models import ProjectContext, TokenPairInput


def test_get_token_info__access(mock_access_token, expires_at, mock_subject_id):
    """Test get_token_info with an access token."""
    res = test_module.get_token_info(mock_access_token)
    assert res.expires_at == expires_at
    assert res.subject_id == mock_subject_id


def test_get_token_info__refresh(mock_refresh_token, mock_subject_id):
    """Test get_token_info with a refresh token."""
    res = test_module.get_token_info(mock_refresh_token)
    assert res.expires_at is None
    assert res.subject_id == mock_subject_id


@patch("auth.service.keycloak_openid.userinfo")
def test_get_user_info__valid(
    mock_userinfo,
    mock_access_token,
    mock_user_info_valid,
    mock_user_groups_valid,
    mock_subject_id,
):
    """Test get_user_info with a valid access token."""
    mock_userinfo.return_value = mock_user_info_valid
    res = test_module.get_user_info(mock_access_token)
    assert res.subject_id == mock_subject_id
    assert res.groups == mock_user_groups_valid


@patch("auth.service.keycloak_openid.userinfo")
def test_validate_access_token(
    mock_userinfo,
    mock_access_token,
    mock_access_token_expired,
    mock_user_info_valid,
    mock_user_info_no_groups,
    mock_subject_id,
    expires_at,
    mock_project_context,
):
    """Test validate_access_token with a valid access token and no project context."""

    # user info with groups and no context. It should pass.
    mock_userinfo.return_value = mock_user_info_valid
    res = test_module.validate_access_token(mock_access_token)
    assert res.subject_id == mock_subject_id
    assert res.expires_at == expires_at

    # user info without groups or project context. It should still pass.
    mock_userinfo.return_value = mock_user_info_no_groups
    res = test_module.validate_access_token(mock_access_token)
    assert res.subject_id == mock_subject_id
    assert res.expires_at == expires_at

    # user info with groups and with context. It should pass.
    mock_userinfo.return_value = mock_user_info_valid
    res = test_module.validate_access_token(mock_access_token, project_context=mock_project_context)
    assert res.subject_id == mock_subject_id
    assert res.expires_at == expires_at

    # user info without groups and with context. It should raise.
    mock_userinfo.return_value = mock_user_info_no_groups
    with pytest.raises(HTTPException):
        test_module.validate_access_token(mock_access_token, project_context=mock_project_context)

    # expired access token. It should raise.
    mock_userinfo.return_value = mock_user_info_valid
    with pytest.raises(HTTPException):
        test_module.validate_access_token(mock_access_token_expired)

    # user info without groups and mismatching context. It should raise.
    project_context = ProjectContext(
        virtual_lab_id=mock_project_context.virtual_lab_id, project_id="foo"
    )
    mock_userinfo.return_value = mock_user_info_valid
    with pytest.raises(HTTPException):
        test_module.validate_access_token(mock_access_token, project_context=project_context)

    # user info without groups and mismatching context. It should raise.
    project_context = ProjectContext(
        virtual_lab_id="foo", project_id=mock_project_context.project_id
    )
    mock_userinfo.return_value = mock_user_info_valid
    with pytest.raises(HTTPException):
        test_module.validate_access_token(mock_access_token, project_context=project_context)

    # user info with groups and mismatching context. It should raise.
    user_info = mock_user_info_valid.copy()
    user_info["groups"] = [f"/proj/{mock_project_context.project_id}/admin", "/vlab/foo/admin"]
    mock_userinfo.return_value = user_info
    with pytest.raises(HTTPException):
        test_module.validate_access_token(mock_access_token, project_context=mock_project_context)

    # user info fails authentication. It should raise.
    mock_userinfo.side_effect = KeycloakAuthenticationError("Invalid token credentials.")
    with pytest.raises(HTTPException):
        test_module.validate_access_token(mock_access_token)


@patch("auth.service.keycloak_openid.userinfo")
def test_validate_token_pair(
    mock_userinfo,
    mock_access_token,
    mock_refresh_token,
    mock_refresh_token_different_subject_id,
    mock_user_info_valid,
    mock_subject_id,
    expires_at,
):
    """Test validate_token_pair with a valid token pair."""

    # valid and consitent token pair. It should pass.
    mock_userinfo.return_value = mock_user_info_valid
    res = test_module.validate_token_pair(
        TokenPairInput(
            access_token=mock_access_token,
            refresh_token=mock_refresh_token,
        )
    )
    assert res.access_token == mock_access_token
    assert res.refresh_token == mock_refresh_token
    assert res.expires_at == expires_at
    assert res.subject_id == mock_subject_id

    # valid and different subject id. It should raise.
    with pytest.raises(HTTPException):
        test_module.validate_token_pair(
            TokenPairInput(
                access_token=mock_access_token,
                refresh_token=mock_refresh_token_different_subject_id,
            )
        )
