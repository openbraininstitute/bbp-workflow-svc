"""Authentication utilities."""

from datetime import UTC, datetime


def get_timestamp_now() -> int:
    """Return UTC timestamp now."""
    return int(datetime.now(UTC).timestamp())
