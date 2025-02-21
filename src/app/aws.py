"""AWS related module."""

import logging

import boto3
from requests_aws4auth import AWS4Auth

from app.util import make_request

L = logging.getLogger(__name__)


def get_secret(sm_client, secret_name: str) -> str:
    """Get secret from secret manager."""
    return sm_client.get_secret_value(SecretId=secret_name)["SecretString"]


def make_aws_signed_request(
    *, url: str, method: str, body: dict | None, service_name: str, headers: dict
) -> dict:
    """Get IAM authentication headers."""
    session = boto3.Session()
    credentials = session.get_credentials()

    auth = AWS4Auth(
        region=session.region_name,
        service=service_name,
        refreshable_credentials=credentials,
    )

    return make_request(
        url=url,
        method=method,
        data=body,
        auth=auth,
        headers=headers,
    )
