"""Utility functions for the Workflow Service.

This module provides common utility functions used throughout the service,
including environment variable handling and other helper functions.
"""

import os

import requests


def get_env(name: str, required: bool = False) -> str:
    """Get a required environment variable or raise an error."""
    value = os.getenv(name, None)

    if not required:
        return value

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
        error_msg = (
            f"Request failed:\n"
            f"URL: {url}\n"
            f"Method: {method}\n"
            f"Status code: {response.status_code}\n"
            f"Response headers: {dict(response.headers)}\n"
            f"Response body: {response.text}"
        )
        raise RuntimeError(error_msg) from e

    return response
