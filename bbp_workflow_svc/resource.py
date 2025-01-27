"""HPC resource API management module."""

import logging
import time
from dataclasses import dataclass
from datetime import datetime

import boto3
import requests
from requests_aws4auth import AWS4Auth

from bbp_workflow_svc.aws import get_secret

L = logging.getLogger(__name__)


REQUEST_TIMEOUT = 60


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
    if auth is None:
        # Create a session with AWS SigV4 signing
        session = boto3.Session()
        credentials = session.get_credentials()

        # Create request headers with AWS SigV4 authentication
        auth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            session.region_name,
            "execute-api",
            session_token=credentials.token,
        )

    # returns secret for ssh key
    post_response = request_cluster(
        api_url=api_url,
        cluster_id=cluster_id,
        auth=auth,
    )

    if post_response.status_code != 200:
        L.error("Failed to allocate head node: %s", post_response.text)
        raise RuntimeError(f"Failed to allocate head node: {post_response.text}")

    private_ssh_key = get_secret(
        sm_client=boto3.client("secretsmanager"),
        secret_name=post_response.json()["cluster"]["private_ssh_key_arn"],
    )

    get_response = wait_for_cluster_ready(
        api_url=api_url,
        cluster_id=cluster_id,
        auth=auth,
    )

    if get_response.status_code != 200:
        L.error("Failed to provision resources: %s", get_response.text)
        raise RuntimeError(f"Failed to provision resources: {get_response.text}")

    private_head_node_ip = get_response.json().get("headNode").get("privateIpAddress")

    return ClusterLoginInfo(
        ssh_key=private_ssh_key,
        head_node_ip=private_head_node_ip,
    )


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
    return requests.post(
        _endpoint(api_url=api_url, cluster_id=cluster_id),
        auth=auth,
        timeout=REQUEST_TIMEOUT,
    )


def get_cluster_status(*, api_url: str, cluster_id: ClusterID, auth: dict | None) -> dict:
    """Get cluster status response."""
    return requests.get(
        _endpoint(api_url=api_url, cluster_id=cluster_id),
        auth=auth,
        timeout=REQUEST_TIMEOUT,
    )


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

        status = response.json().get("clusterStatus")

        if status == "CREATE_COMPLETE":
            L.info("Cluster %s is ready.", cluster_id)
            return response

        if status == "CREATE_FAILED":
            L.error("Cluster %s failed to become ready.", cluster_id)
            return None

        L.debug("Cluster %s status: %s", cluster_id, status)

        time.sleep(check_interval)

    L.error("Timeout waiting for cluster %s to become ready.", cluster_id)

    return None


def _endpoint(*, api_url: str, cluster_id: ClusterID) -> str:
    """Construct the endpoint for the HPC provisioner API.

    Note:
        project_id and vlab_id parameters should be sorted alphabetically.
    """
    project_id, vlab_id = cluster_id.project, cluster_id.virtual_lab
    return f"{api_url}/pcluster?project_id={project_id}&vlab_id={vlab_id}"
