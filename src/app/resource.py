"""HPC resource API management module."""

import logging
import time
from dataclasses import dataclass
from datetime import datetime

import boto3
import requests

from app.aws import get_secret, make_aws_signed_request
from app.exception import (
    ClusterFailedToGetStatusError,
    ClusterRequestFailedError,
    ClusterRequestTimeoutError,
    ClusterResponseEntryError,
    ClusterUnknownStatusError,
)

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


def request_cluster_and_wait(*, api_url: str, cluster_id: ClusterID) -> dict:
    """Request a cluster formation and wait until it's ready.

    Args:
        cluster_id: The Cluster ID to request.

    Raises:
        ClusterError: If a cluster operation fails.
    """
    # returns response with secret for ssh key
    post_response = request_cluster(
        api_url=api_url,
        cluster_id=cluster_id,
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

    Raises:
        ClusterResponseEntryError: If the cluster response entry cannot be retrieved.
    """
    if not (data := response.json()):
        raise ClusterResponseEntryError(f"Response has no data: {response.text}")

    value = data
    keys = key.split(".")

    try:
        for current_key in keys:
            value = value[current_key]
    except KeyError as e:
        raise ClusterResponseEntryError(f"Failed to get cluster response entry: {e}") from e

    return value


def request_cluster(*, api_url: str, cluster_id: ClusterID) -> dict:
    """Request cluster allocation.

    cluster_id: The Cluster ID to request.

    Raises:
        ClusterRequestFailedError: If the cluster request fails.

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
    try:
        response = make_aws_signed_request(
            url=_endpoint(api_url=api_url, cluster_id=cluster_id),
            method="POST",
            body=None,
            service_name="execute-api",
            headers={},
        )
    except requests.exceptions.HTTPError as e:
        L.error("Failed to allocate head node: %s", e)
        raise ClusterRequestFailedError(f"Failed to request head node: {e}") from e

    L.info("%s was successfully requested.", cluster_id)
    return response


def get_cluster_status(*, api_url: str, cluster_id: ClusterID) -> dict:
    """Get cluster status response.

    Args:
        api_url: The API URL.
        cluster_id: The Cluster ID to get the status of.

    Raises:
        ClusterFailedToGetStatusError: If the cluster status cannot be retrieved.
    """
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
        raise ClusterFailedToGetStatusError(f"Failed to get cluster status: {e}") from e


def wait_for_cluster_ready(
    *,
    api_url: str,
    cluster_id: ClusterID,
    timeout: int = 3600,
    check_interval: int = 60,
) -> dict | None:
    """Wait for cluster to become ready within the given timeout.

    Raises:
        ClusterError: If a cluster operation fails.

    Args:
        api_url: The API URL.
        cluster_id: The Cluster ID to wait for.
        timeout: The timeout for the cluster to become ready.
        check_interval: The interval to check the cluster status.

    Returns:
        The response from the HPC resource provisioner API.
    """
    start_time = datetime.now()

    # wait for a little while to ensure the cluster status is visible
    while (datetime.now() - start_time).total_seconds() < 10:
        L.info("Attempting to get cluster status for %s", cluster_id)
        try:
            response = get_cluster_status(
                api_url=api_url,
                cluster_id=cluster_id,
            )
            status = _fetch_response_entry(response, "clusterStatus")
            break
        except ClusterFailedToGetStatusError:
            L.info("Failed to get cluster status for %s.", cluster_id)
            time.sleep(2)
    else:
        raise ClusterFailedToGetStatusError(f"Failed to get cluster status for {cluster_id}.")

    # and now wait for the cluster to become ready
    while (datetime.now() - start_time).total_seconds() < timeout:

        L.info("Handling cluster status: %s", status)

        match status:
            case "CREATE_COMPLETE":
                L.info("Cluster %s is ready.", cluster_id)
                return response

            case "CREATE_FAILED" | "DELETE_FAILED" | "DELETE_IN_PROGRESS":
                L.error("Cluster %s failed to become ready.", cluster_id)
                return None

            case "CREATE_IN_PROGRESS" | "UPDATE_IN_PROGRESS":
                L.info("Cluster %s is still being created/updated.", cluster_id)

                time.sleep(check_interval)

                response = get_cluster_status(
                    api_url=api_url,
                    cluster_id=cluster_id,
                )

                status = _fetch_response_entry(response, "clusterStatus")
                L.debug("Cluster %s status: %s", cluster_id, status)
                continue

            case _:
                L.error("Unexpected cluster status: %s", status)
                raise ClusterUnknownStatusError(f"Unexpected cluster status: {status}")

    L.error("Timeout waiting for cluster %s to become ready.", cluster_id)
    raise ClusterRequestTimeoutError(f"Timeout waiting for cluster {cluster_id} to become ready.")


def _endpoint(*, api_url: str, cluster_id: ClusterID) -> str:
    """Construct the endpoint for the HPC provisioner API.

    Note:
        project_id and vlab_id parameters should be sorted alphabetically.
    """
    proj_id, vlab_id = cluster_id.project, cluster_id.virtual_lab
    short_vlab_id = vlab_id.split("-")[0]
    short_proj_id = proj_id.split("-")[0]
    return f"{api_url}/pcluster?project_id={short_proj_id}&vlab_id={short_vlab_id}&dev=True"
