class TaskClientError(Exception):
    """Base exception raised by task-client implementations."""


class TaskNotFoundError(TaskClientError):
    """Raised when a task session no longer exists or cannot be resolved."""


class TaskAlreadyFinishedError(TaskClientError):
    """Raised when the caller tries to interact with a task that already finished."""


class CapacityExceededError(TaskClientError):
    """Base error raised when runtime capacity has been reached."""

    def __init__(self, message: str, *, reason: str | None = None) -> None:
        """
        Create a capacity error without exposing configured limit values.

        Args:
            message: Sanitized description of the capacity failure.
            reason: Stable server reason identifying the capacity category.

        """
        super().__init__(message)
        self.reason = reason


class RunCapacityExceededError(CapacityExceededError):
    """Raised when runtime active-run capacity has been reached."""


class TaskCapacityExceededError(CapacityExceededError):
    """Raised when runtime active-task capacity has been reached."""


class OperationCapacityExceededError(CapacityExceededError):
    """Raised when runtime in-flight operation capacity has been reached."""


class IdempotencyCapacityExceededError(CapacityExceededError):
    """Raised when runtime retained idempotency history capacity has been reached."""


class TaskExecutionError(TaskClientError):
    """Raised when the underlying task runtime fails during task leasing or tool execution."""
