import jwt
import pytest

from auth.models import ProjectContext, TokenPairInput
from auth.util import get_timestamp_now

MOCK_VIRTUAL_LAB_ID = "ea3273ac-684f-4828-a651-ba17c9d6c41d"
MOCK_PROJECT_ID = "67ee6c17-c3c9-408d-9fa4-ea033dc05da6"
MOCK_SUBJECT_ID = "098ed78a-655a-4108-ac66-144a01e444a1"


@pytest.fixture(scope="session")
def mock_virtual_lab_id():
    return MOCK_VIRTUAL_LAB_ID


@pytest.fixture(scope="session")
def mock_project_id():
    return MOCK_PROJECT_ID


@pytest.fixture(scope="session")
def mock_project_context():
    return ProjectContext(virtual_lab_id=MOCK_VIRTUAL_LAB_ID, project_id=MOCK_PROJECT_ID)


@pytest.fixture(scope="session")
def mock_subject_id():
    return MOCK_SUBJECT_ID


@pytest.fixture(scope="session")
def issued_at():
    return get_timestamp_now()


@pytest.fixture(scope="session")
def expires_at(issued_at):
    return issued_at + 3600


@pytest.fixture(scope="session")
def mock_access_token_decoded(issued_at, expires_at, mock_subject_id):
    return {
        "exp": expires_at,
        "iat": issued_at,
        "auth_time": 1737712741,
        "jti": "9cec4321-1828-437d-8424-6358610f6e8a",
        "iss": "https://www.openbraininstitute.org/auth/realms/SBO",
        "aud": "account",
        "sub": mock_subject_id,
        "typ": "Bearer",
        "azp": "bbp-workflow",
        "session_state": "c419af81-e00a-442a-b7cb-5cbbd2325799",
        "acr": "0",
        "allowed-origins": [
            "https://openbluebrain.com",
            "https://openbrainplatform.org",
            "http://localhost:3000*",
            "https://sbo-core-webapp.shapes-registry.org",
        ],
        "realm_access": {"roles": ["offline_access", "uma_authorization", "default-roles-sbo"]},
        "resource_access": {
            "account": {"roles": ["manage-account", "manage-account-links", "view-profile"]},
            "sbo-core-webapp": {"roles": ["restricted-access"]},
        },
        "scope": "openid profile email",
        "sid": "ba0558ed-6bf4-4a51-995e-acf6443d566e",
        "email_verified": False,
        "name": "John Smith",
        "preferred_username": "johnsmith",
        "given_name": "John",
        "family_name": "Smith",
        "email": "john.smit@openbraininstitute.com",
    }


@pytest.fixture(scope="session")
def mock_access_token(mock_access_token_decoded):
    return jwt.encode(mock_access_token_decoded, key=None, algorithm="none")


@pytest.fixture(scope="session")
def mock_access_token_expired(mock_access_token_decoded):
    data = mock_access_token_decoded.copy()
    data["exp"] = get_timestamp_now() - 1
    return jwt.encode(data, key=None, algorithm="none")


@pytest.fixture(scope="session")
def mock_refresh_token_decoded(issued_at, mock_subject_id):
    return {
        "iat": issued_at,
        "jti": "9cec4321-1828-437d-8424-6358610f6e8a",
        "iss": "https://www.openbraininstitute.org/auth/realms/SBO",
        "aud": "https://www.openbraininstitute.org/auth/realms/SBO",
        "sub": mock_subject_id,
        "typ": "Offline",
        "azp": "bbp-workflow",
        "sid": "ba0558ed-6bf4-4a51-995e-acf6443d566e",
        "scope": "web-origins openid profile email roles groups offline_access basic",
    }


@pytest.fixture(scope="session")
def mock_refresh_token(mock_refresh_token_decoded):
    return jwt.encode(mock_refresh_token_decoded, key=None, algorithm="none")


@pytest.fixture(scope="session")
def mock_refresh_token_different_subject_id(mock_refresh_token_decoded):
    data = mock_refresh_token_decoded.copy()
    data["sub"] = "different-subject-id"
    return jwt.encode(data, key=None, algorithm="none")


@pytest.fixture(scope="session")
def mock_token_pair_input(mock_access_token, mock_refresh_token):
    return TokenPairInput(
        access_token=mock_access_token,
        refresh_token=mock_refresh_token,
    )


@pytest.fixture(scope="session")
def mock_user_groups_valid(mock_virtual_lab_id, mock_project_id):
    return [
        "BBP-USERS",
        f"/vlab/{mock_virtual_lab_id}/admin",
        f"/proj/{mock_project_id}/admin",
    ]


@pytest.fixture(scope="session")
def mock_user_info_valid(mock_subject_id, mock_user_groups_valid):
    return {
        "email": "john.smith@openbraininstitute.org",
        "email_verified": False,
        "family_name": "Smith",
        "given_name": "John",
        "name": "John Smith",
        "preferred_username": "ez_test_account",
        "sub": mock_subject_id,
        "groups": mock_user_groups_valid,
    }


@pytest.fixture(scope="session")
def mock_user_info_no_groups(mock_subject_id):
    return {
        "email": "john.smith@openbraininstitute.org",
        "email_verified": False,
        "family_name": "Smith",
        "given_name": "John",
        "name": "John Smith",
        "preferred_username": "ez_test_account",
        "sub": mock_subject_id,
    }
