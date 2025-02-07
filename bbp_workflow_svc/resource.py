"""HPC resource API management module."""

import logging
import time
from dataclasses import dataclass
from datetime import datetime

import boto3
import requests

from bbp_workflow_svc.aws import get_secret, make_aws_signed_request

L = logging.getLogger(__name__)


@dataclass
class ClusterID:
    """HPC Cluster unique identifier.

    Attributes:
        project_id: The project ID. Example: "proj30"
        vlab_id: The Virtual lab ID. Example: "vlab2"

    """

    project: str
    virtual_lab: str

    def __repr__(self):
        """Return a representation of the ClusterID."""
        return f"ClusterID(project_id={self.project}, vlab_id={self.virtual_lab})"

    def __str__(self):
        """Return a string representation of the ClusterID."""
        return self.__repr__()


@dataclass
class ClusterLoginInfo:
    """
    Response from the HPC resource provisioner API.

    Attributes:
        ssh_key: The private SSH key for the head node.
        head_node_ip: The private IP address of the head node.
    """

    ssh_key: str
    head_node_ip: str


def request_cluster_and_wait(*, api_url: str, cluster_id: ClusterID, auth: dict | None) -> dict:
    """Request a cluster formation and wait until it's ready.

    Args:
        cluster_id: The Cluster ID to request.
        auth: Optional authentication headers.
    """
    # returns response with secret for ssh key
    post_response = request_cluster(
        api_url=api_url,
        cluster_id=cluster_id,
        auth=auth,
    )

    secret_name = _fetch_response_entry(post_response, "cluster.private_ssh_key_arn")

    private_ssh_key = get_secret(
        sm_client=boto3.client("secretsmanager"),
        secret_name=secret_name,
    )

    # returns response with head node ip
    get_response = wait_for_cluster_ready(
        api_url=api_url,
        cluster_id=cluster_id,
        auth=auth,
    )

    private_head_node_ip = _fetch_response_entry(get_response, "headNode.privateIpAddress")

    return ClusterLoginInfo(
        ssh_key=private_ssh_key,
        head_node_ip=private_head_node_ip,
    )


def _fetch_response_entry(response: requests.Response, key: str) -> dict:
    """Fetch an entry from the response JSON.

    key is a dot-separated path to the entry, e.g. "foo.bar.baz" corresponding to
    the JSON entry `{"foo": {"bar": {"baz": "qux"}}}`.
    """

    if not (data := response.json()):
        raise RuntimeError(f"Response has no data: {response.text}")

    value = data
    keys = key.split(".")

    try:
        for current_key in keys:
            value = value[current_key]
    except KeyError:
        raise RuntimeError(f"Response data has no key: {key}")

    return value


def request_cluster(*, api_url: str, cluster_id: ClusterID, auth: dict | None) -> dict:
    """Request cluster allocation.

    cluster_id: The Cluster ID to request.

    Returns:
        The response from the HPC resource provisioner API.
        Example:
        {
            "cluster": {
                "clusterName": "pcluster-smith-proj02",
                "clusterStatus": "CREATE_REQUEST_RECEIVED",
                "private_ssh_key_arn": "arn..."
            }
        }
    """
    response = make_aws_signed_request(
        url=_endpoint(api_url=api_url, cluster_id=cluster_id),
        method="POST",
        body=None,
        service_name="execute-api",
        headers={},
    )

    return response


def get_cluster_status(*, api_url: str, cluster_id: ClusterID, auth: dict | None = None) -> dict:
    """Get cluster status response."""
    try:
        return make_aws_signed_request(
            url=_endpoint(api_url=api_url, cluster_id=cluster_id),
            method="GET",
            body=None,
            service_name="execute-api",
            headers={},
        )
    except requests.exceptions.HTTPError as e:
        L.error("Failed to get cluster status: %s", e)
        raise RuntimeError(f"Failed to get cluster status: {e}") from e


def wait_for_cluster_ready(
    *,
    api_url: str,
    cluster_id: ClusterID,
    timeout: int = 3600,
    check_interval: int = 60,
    auth: dict | None,
) -> dict | None:
    """Wait for cluster to become ready within the given timeout."""
    start_time = datetime.now()

    while (datetime.now() - start_time).total_seconds() < timeout:

        response = get_cluster_status(
            api_url=api_url,
            cluster_id=cluster_id,
            auth=auth,
        )

        status = _fetch_response_entry(response, "clusterStatus")

        if status == "CREATE_COMPLETE":
            L.info("Cluster %s is ready.", cluster_id)
            return response

        if status == "CREATE_FAILED":
            L.error("Cluster %s failed to become ready.", cluster_id)
            return None

        L.debug("Cluster %s status: %s", cluster_id, status)

        time.sleep(check_interval)

    L.error("Timeout waiting for cluster %s to become ready.", cluster_id)

    raise RuntimeError(f"Timeout waiting for cluster {cluster_id} to become ready.")


def _endpoint(*, api_url: str, cluster_id: ClusterID) -> str:
    """Construct the endpoint for the HPC provisioner API.

    Note:
        project_id and vlab_id parameters should be sorted alphabetically.
    """
    project_id, vlab_id = cluster_id.project, cluster_id.virtual_lab
    return f"{api_url}/pcluster?project_id={project_id}&vlab_id={vlab_id}"
