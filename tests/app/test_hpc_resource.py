from unittest.mock import Mock, patch

import pytest

from app import exception
from app import hpc_resource as test_module
from app.testing import patchenv

# Test data
MOCK_CLUSTER_ID = test_module.ClusterID(project="proj30", virtual_lab="vlab2")
MOCK_SSH_KEY = "mock-private-key"
MOCK_IP = "10.0.0.1"
MOCK_SECRET_ARN = "arn:aws:secretsmanager:region:account:secret:name"
MOCK_API_URL = "https://api-url"


class MockResponse:
    def __init__(self, json_data, text=""):
        self._json_data = json_data
        self.text = text

    def json(self):
        return self._json_data


@pytest.fixture
def mock_cluster_id():
    return test_module.ClusterID(project="proj30", virtual_lab="vlab2")


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


@patch("app.hpc_resource.make_aws_signed_request")
def test_request_cluster(mock_make_aws_signed_request, mock_successful_post_response):
    mock_make_aws_signed_request.return_value = mock_successful_post_response

    response = test_module.request_cluster(api_url=MOCK_API_URL, cluster_id=MOCK_CLUSTER_ID)

    mock_make_aws_signed_request.assert_called_once()
    assert response.status_code == 200
    assert response.json()["cluster"]["private_ssh_key_arn"] == MOCK_SECRET_ARN


@patch("app.hpc_resource.make_aws_signed_request")
def test_get_cluster_status(mock_make_aws_signed_request, mock_successful_get_response):
    mock_make_aws_signed_request.return_value = mock_successful_get_response

    response = test_module.get_cluster_status(
        api_url=MOCK_API_URL,
        cluster_id=MOCK_CLUSTER_ID,
    )

    mock_make_aws_signed_request.assert_called_once()
    assert response.status_code == 200
    assert response.json()["headNode"]["privateIpAddress"] == MOCK_IP


@patch("app.hpc_resource.make_aws_signed_request")
def test_wait_for_cluster_ready_success(mock_make_aws_signed_request, mock_successful_get_response):
    mock_make_aws_signed_request.return_value = mock_successful_get_response

    response = test_module.wait_for_cluster_ready(
        api_url=MOCK_API_URL,
        cluster_id=MOCK_CLUSTER_ID,
        timeout=10,
        check_interval=1,
    )

    assert response == mock_successful_get_response
    mock_make_aws_signed_request.assert_called()


@patch("app.hpc_resource.make_aws_signed_request")
def test_wait_for_cluster_ready_failure(mock_make_aws_signed_request):
    mock_response = Mock()
    mock_response.json.return_value = {"clusterStatus": "CREATE_FAILED"}
    mock_make_aws_signed_request.return_value = mock_response

    response = test_module.wait_for_cluster_ready(
        api_url=MOCK_API_URL,
        cluster_id=MOCK_CLUSTER_ID,
        timeout=10,
        check_interval=1,
    )

    assert response is None
    mock_make_aws_signed_request.assert_called()


@patch("app.hpc_resource.get_cluster_status")
def test_wait_for_cluster_ready_timeout(mock_get_cluster_status):
    mock_get_cluster_status.return_value = MockResponse({"clusterStatus": "CREATE_IN_PROGRESS"})

    with pytest.raises(exception.ClusterRequestTimeoutError, match="Timeout waiting for cluster"):
        test_module.wait_for_cluster_ready(
            api_url=MOCK_API_URL,
            cluster_id=MOCK_CLUSTER_ID,
            check_interval=0.01,
            timeout=0.01,
        )


def test_fetch_response_entry_success():
    # Test nested data retrieval
    response = MockResponse(
        {
            "cluster": {
                "private_ssh_key_arn": "arn:aws:secretsmanager:123",
                "headNode": {"privateIpAddress": "10.0.0.1"},
            }
        }
    )

    res = test_module._fetch_response_entry(response, "cluster.private_ssh_key_arn")
    assert res == "arn:aws:secretsmanager:123"

    res = test_module._fetch_response_entry(response, "cluster.headNode.privateIpAddress")
    assert res == "10.0.0.1"


def test_fetch_response_entry_empty_response():
    response = MockResponse(None, text="Empty response")

    with pytest.raises(
        exception.ClusterResponseEntryError,
        match="Response has no data: Empty response",
    ):
        test_module._fetch_response_entry(response, "any.key")


def test_fetch_response_entry_missing_key():
    response = MockResponse({"cluster": {"someOtherKey": "value"}})

    with pytest.raises(
        exception.ClusterResponseEntryError,
        match="Failed to get cluster response entry: 'private_ssh_key_arn'",
    ):
        test_module._fetch_response_entry(response, "cluster.private_ssh_key_arn")


@patch("app.hpc_resource.request_cluster")
@patch("app.hpc_resource.get_secret")
@patch("app.hpc_resource.wait_for_cluster_ready")
def test_request_cluster_and_wait(
    mock_wait_for_cluster_ready, mock_get_secret, mock_request_cluster
):
    mock_request_cluster.return_value = MockResponse(
        {"cluster": {"private_ssh_key_arn": "arn:aws:secretsmanager:123"}}
    )

    mock_get_secret.return_value = "secret-key"

    mock_wait_for_cluster_ready.return_value = MockResponse(
        {"headNode": {"privateIpAddress": "10.0.0.1"}}
    )

    result = test_module.request_cluster_and_wait(api_url=MOCK_API_URL, cluster_id=None)

    assert result == test_module.ClusterLoginInfo(ssh_key="secret-key", head_node_ip="10.0.0.1")
