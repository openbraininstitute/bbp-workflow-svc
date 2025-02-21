"""Environment configuration for the Workflow Service.

This module handles environment-specific configuration and provides
functions to access environment variables required by the service.
"""

from app.util import get_env

# The virtual lab project id
PROJECT_ID = get_env(name="PROJECT_ID", required=True)

# The virtual lab id
VIRTUAL_LAB_ID = get_env(name="VIRTUAL_LAB_ID", required=True)

DB_API_URL = get_env(name="DB_API_URL", required=True)


def get_hpc_resource_provisioner_api_url() -> str:
    """Get the HPC resource provisioner API URL from the environment."""
    return get_env(name="HPC_RESOURCE_PROVISIONER_API_URL", required=True)
