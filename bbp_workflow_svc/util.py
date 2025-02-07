"""Utility functions for the Workflow Service.

This module provides common utility functions used throughout the service,
including environment variable handling and other helper functions.
"""

import os

import requests


def get_required_env(name: str) -> str:
    """Get a required environment variable or raise an error."""
    value = os.getenv(name)
    if value is None:
        raise ValueError(f"Required environment variable '{name}' is not set.")
    if not value.strip():
        raise ValueError(f"Required environment variable '{name}' cannot be empty.")
    return value


def make_request(
    url: str,
    *,
    method: str,
    headers: dict | None = None,
    data: dict | None = None,
    auth: tuple[str, str] | None = None,
    timeout: int = 10,
) -> requests.Response:
    """Make a request to the given URL with the given method and data."""
    response = requests.request(method, url, headers=headers, json=data, auth=auth, timeout=timeout)

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Failed to make request: {response.text}") from e

    return response
