"""AWS related module."""

import logging

L = logging.getLogger(__name__)


def get_secret(sm_client, secret_name: str) -> str:
    """Get secret from secret manager."""
    return sm_client.get_secret_value(SecretId=secret_name)["SecretString"]
