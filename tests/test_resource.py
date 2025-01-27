from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from bbp_workflow_svc import resource as test_module
from bbp_workflow_svc.testing import patchenv

# Test data
MOCK_CLUSTER_ID = test_module.ClusterID(project="proj30", virtual_lab="vlab2")
MOCK_SSH_KEY = "mock-private-key"
MOCK_IP = "10.0.0.1"
MOCK_SECRET_ARN = "arn:aws:secretsmanager:region:account:secret:name"
MOCK_API_URL = "https://api-url"


@pytest.fixture
def mock_auth():
    return {"Authorization": "mock-auth"}


@pytest.fixture
def mock_successful_post_response():
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "cluster": {
            "clusterName": "pcluster-test",
            "clusterStatus": "CREATE_REQUEST_RECEIVED",
            "private_ssh_key_arn": MOCK_SECRET_ARN,
        }
    }
    return mock_response


@pytest.fixture
def mock_successful_get_response():
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "headNode": {"privateIpAddress": MOCK_IP},
        "clusterStatus": "CREATE_COMPLETE",
    }
    return mock_response


def test_cluster_id_repr():
    cluster_id = MOCK_CLUSTER_ID
    expected = f"ClusterID(project_id={cluster_id.project}, vlab_id={cluster_id.virtual_lab})"
    assert str(cluster_id) == expected
    assert repr(cluster_id) == expected


@patchenv(HPC_RESOURCE_PROVISIONER_API_URL="foo")
def test_endpoint():
    expected = f"{MOCK_API_URL}/pcluster?project_id=proj30&vlab_id=vlab2"
    assert (
        test_module._endpoint(
            api_url=MOCK_API_URL,
            cluster_id=MOCK_CLUSTER_ID,
        )
        == expected
    )


@patch("bbp_workflow_svc.resource.requests.post")
def test_request_cluster(mock_post, mock_auth, mock_successful_post_response):
    mock_post.return_value = mock_successful_post_response

    response = test_module.request_cluster(
        api_url=MOCK_API_URL, cluster_id=MOCK_CLUSTER_ID, auth=mock_auth
    )

    mock_post.assert_called_once()
    assert response.status_code == 200
    assert response.json()["cluster"]["private_ssh_key_arn"] == MOCK_SECRET_ARN


@patch("bbp_workflow_svc.resource.requests.get")
def test_get_cluster_status(mock_get, mock_auth, mock_successful_get_response):
    mock_get.return_value = mock_successful_get_response

    response = test_module.get_cluster_status(
        api_url=MOCK_API_URL, cluster_id=MOCK_CLUSTER_ID, auth=mock_auth
    )

    mock_get.assert_called_once()
    assert response.status_code == 200
    assert response.json()["headNode"]["privateIpAddress"] == MOCK_IP


@patch("bbp_workflow_svc.resource.requests.get")
def test_wait_for_cluster_ready_success(mock_get, mock_auth, mock_successful_get_response):
    mock_get.return_value = mock_successful_get_response

    response = test_module.wait_for_cluster_ready(
        api_url=MOCK_API_URL,
        cluster_id=MOCK_CLUSTER_ID,
        timeout=10,
        check_interval=1,
        auth=mock_auth,
    )

    assert response == mock_successful_get_response
    mock_get.assert_called()


@patch("bbp_workflow_svc.resource.requests.get")
def test_wait_for_cluster_ready_failure(mock_get, mock_auth):
    mock_response = Mock()
    mock_response.json.return_value = {"clusterStatus": "CREATE_FAILED"}
    mock_get.return_value = mock_response

    response = test_module.wait_for_cluster_ready(
        api_url=MOCK_API_URL,
        cluster_id=MOCK_CLUSTER_ID,
        timeout=10,
        check_interval=1,
        auth=mock_auth,
    )

    assert response is None
    mock_get.assert_called()


@patch("bbp_workflow_svc.resource.boto3.Session")
@patch("bbp_workflow_svc.resource.boto3.client")
@patch("bbp_workflow_svc.resource.requests.post")
@patch("bbp_workflow_svc.resource.requests.get")
@patch("bbp_workflow_svc.resource.get_secret")
def test_request_cluster_and_wait(
    mock_get_secret,
    mock_get,
    mock_post,
    mock_boto3_client,
    mock_boto3_session,
    mock_successful_post_response,
    mock_successful_get_response,
):
    # Setup mocks
    mock_post.return_value = mock_successful_post_response
    mock_get.return_value = mock_successful_get_response
    mock_get_secret.return_value = MOCK_SSH_KEY

    # Mock AWS session
    mock_credentials = Mock()
    mock_credentials.access_key = "mock-access-key"
    mock_credentials.secret_key = "mock-secret-key"
    mock_credentials.token = "mock-token"
    mock_session = Mock()
    mock_session.get_credentials.return_value = mock_credentials
    mock_session.region_name = "mock-region"
    mock_boto3_session.return_value = mock_session

    result = test_module.request_cluster_and_wait(
        api_url=MOCK_API_URL, cluster_id=MOCK_CLUSTER_ID, auth=None
    )

    assert isinstance(result, test_module.ClusterLoginInfo)
    assert result.ssh_key == MOCK_SSH_KEY
    assert result.head_node_ip == MOCK_IP

    mock_post.assert_called_once()
    mock_get.assert_called()
    mock_get_secret.assert_called_once_with(
        sm_client=mock_boto3_client.return_value, secret_name=MOCK_SECRET_ARN
    )
