"""Environment configuration for the Workflow Service.

This module handles environment-specific configuration and provides
functions to access environment variables required by the service.
"""

from bbp_workflow_svc.util import get_required_env


def get_hpc_resource_provisioner_api_url() -> str:
    """Get the HPC resource provisioner API URL from the environment."""
    return get_required_env(name="HPC_RESOURCE_PROVISIONER_API_URL")
