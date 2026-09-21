from ..errors import TaskClientError


class RemoteClientError(TaskClientError):
    """Base error for remote task-client failures."""

    def __init__(
        self,
        message: str,
        *,
        reason: str | None = None,
        request_id: str | None = None,
        retryable: bool = False,
        retry_after_seconds: float | None = None,
    ) -> None:
        """
        Create a sanitized transport-neutral remote error.

        Args:
            message: Safe public failure description.
            reason: Stable machine-readable server reason.
            request_id: Opaque server request identifier.
            retryable: Whether repeating the logical request can be safe.
            retry_after_seconds: Bounded server-provided retry delay.

        """
        super().__init__(message)
        self.reason = reason
        self.request_id = request_id
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds


class RemoteClientStateError(RemoteClientError):
    """Raised when an operation is invalid for the client or session state."""


class RemoteRequestError(RemoteClientError):
    """Raised when a remote request is invalid."""


class RemoteAuthenticationError(RemoteClientError):
    """Raised when the bearer credential is missing or invalid."""


class RemoteAuthorizationError(RemoteClientError):
    """Raised when the authenticated principal lacks permission."""


class RemoteRunNotFoundError(RemoteClientError):
    """Raised when a remote run cannot be resolved."""


class RemoteConflictError(RemoteClientError):
    """Raised when an idempotency key conflicts with another request."""


class RemoteSessionLostError(RemoteClientError):
    """Raised when runtime state for an active run or task was lost."""


class CompetitionClosedError(RemoteClientError):
    """Raised when the competition accepts no runs at the current server time."""


class RemoteRateLimitError(RemoteClientError):
    """Raised when the service applies a generic request rate limit."""


class RemoteUnavailableError(RemoteClientError):
    """Raised when the remote runtime is temporarily unavailable."""


class RemoteTransportError(RemoteClientError):
    """Raised for connection, channel, or RPC deadline failures."""


class RemoteProtocolError(RemoteClientError):
    """Raised for incompatible or malformed protocol responses."""


class RemoteServerError(RemoteClientError):
    """Raised for unexpected remote runtime failures."""
