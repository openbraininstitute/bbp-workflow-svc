"""Testing utilities for the Workflow Service.

This module provides helper functions and utilities to assist with testing,
including environment variable mocking and other test-specific functionality.
"""

import os
from unittest.mock import patch


def patchenv(**envvars):
    """Patch function environment."""
    return patch.dict(os.environ, envvars, clear=True)
