"""Token storage for the auth service."""

from auth.models import TokenPair


class TokenStorage:
    """In memory token storage."""

    def __init__(self):
        """Initialize an empty token storage."""
        self._storage: dict[str, TokenPair] = {}

    def add_token_pair(self, token_pair: TokenPair) -> None:
        """Add a token pair to the storage."""
        self._storage[token_pair.access_token] = token_pair

    def get_token_pair(self, access_token: str) -> TokenPair:
        """Get a token pair from the storage."""
        return self._storage[access_token]

    def update_token_pair(self, access_token: str, token_pair: TokenPair) -> None:
        """Update a token pair in the storage."""
        self._storage[access_token] = token_pair

    def delete_token_pair(self, access_token: str) -> None:
        """Delete a token pair from the storage."""
        del self._storage[access_token]

    def __contains__(self, access_token: str) -> bool:
        """Check if a token pair exists in the storage."""
        return access_token in self._storage

    def clear(self) -> None:
        """Clear the storage."""
        self._storage.clear()
