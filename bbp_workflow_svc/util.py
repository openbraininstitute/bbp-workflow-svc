"""Utility functions for the Workflow Service.

This module provides common utility functions used throughout the service,
including environment variable handling and other helper functions.
"""

import os


def get_required_env(name: str) -> str:
    """Get a required environment variable or raise an error."""
    value = os.getenv(name)
    if value is None:
        raise ValueError(f"Required environment variable '{name}' is not set.")
    if not value.strip():
        raise ValueError(f"Required environment variable '{name}' cannot be empty.")
    return value
