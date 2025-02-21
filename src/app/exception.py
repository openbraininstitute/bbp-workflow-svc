"""Custom exceptions."""


class ClusterError(Exception):
    """Exception raised when a cluster operation fails."""


class ClusterRequestTimeoutError(ClusterError):
    """Exception raised when a cluster request times out."""


class ClusterFailedToGetStatusError(ClusterError):
    """Exception raised when a cluster status cannot be retrieved."""


class ClusterUnknownStatusError(ClusterError):
    """Exception raised when an unknown cluster status is encountered."""


class ClusterRequestFailedError(ClusterError):
    """Exception raised when a cluster request fails."""


class ClusterResponseEntryError(ClusterError):
    """Exception raised when a cluster response entry cannot be retrieved."""
