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


def make_request(url: str, *, method, **kwargs) -> requests.Response:
    """Make a request to the given URL with the given method and data."""
    timeout = kwargs.pop("timeout", 10)
    response = requests.request(method, url, timeout=timeout, **kwargs)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        error_msg = (
            "\n"
            f"  Request failed:\n"
            f"  URL: {url}\n"
            f"  Method: {method}\n"
            f"  Status code: {response.status_code}\n"
            f"  Response body: {response.text}"
        )
        raise requests.exceptions.HTTPError(error_msg) from e

    return response
