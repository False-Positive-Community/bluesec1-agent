import math
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..protocols import PublicTask, TaskResult, ToolCallResult

CloseRunReason = Literal["client_requested", "client_error", "client_interrupted"]


class RemoteModel(BaseModel):
    """Base immutable model for the transport-neutral remote client."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class DeadlinePolicy(RemoteModel):
    """Per-operation gRPC deadlines in seconds."""

    create_run: float = Field(default=60.0, gt=0, le=3600)
    lease_task: float = Field(default=30.0, gt=0, le=3600)
    call_tool: float = Field(default=60.0, gt=0, le=3600)
    abort_task: float = Field(default=15.0, gt=0, le=3600)
    close_run: float = Field(default=15.0, gt=0, le=3600)
    channel_close: float = Field(default=5.0, gt=0, le=3600)


class RetryPolicy(RemoteModel):
    """Bounded SDK-owned retry behavior."""

    max_attempts: int = Field(default=3, ge=1, le=10)
    initial_backoff_seconds: float = Field(default=0.25, ge=0, le=60)
    max_backoff_seconds: float = Field(default=2.0, ge=0, le=60)
    backoff_multiplier: float = Field(default=2.0, ge=1, le=10)
    max_retry_after_seconds: float = Field(default=30.0, gt=0, le=300)

    @model_validator(mode="after")
    def validate_backoff_bounds(self) -> "RetryPolicy":
        """
        Require the maximum backoff to cover the initial backoff.

        Returns:
            Validated retry policy.

        Raises:
            ValueError: If the initial delay exceeds the maximum delay.

        """
        if self.initial_backoff_seconds > self.max_backoff_seconds:
            raise ValueError("initial backoff must not exceed maximum backoff")
        return self


class DynamicValueLimits(RemoteModel):
    """Bounds applied to canonical recursive values and gRPC messages."""

    max_depth: int = Field(default=16, ge=1, le=32)
    max_collection_items: int = Field(default=10_000, ge=1, le=1_000_000)
    max_string_bytes: int = Field(default=1_048_576, ge=1, le=67_108_864)
    max_message_bytes: int = Field(default=4_194_304, ge=1024, le=67_108_864)

    @property
    def grpc_message_bytes(self) -> int:
        """
        Return the configured gRPC send and receive message bound.

        Returns:
            Maximum serialized message size in bytes.

        """
        return self.max_message_bytes


class CreateRunCommand(RemoteModel):
    """Transport-neutral command that creates a new run."""

    idempotency_key: str = Field(min_length=1, max_length=255)
    label: str | None = Field(default=None, max_length=255)
    agent_name: str | None = Field(default=None, max_length=255)
    model_name: str | None = Field(default=None, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)
    arena: str | None = Field(default=None, max_length=64)


class LeaseTaskCommand(RemoteModel):
    """Transport-neutral command that leases the next task."""

    run_id: str = Field(min_length=1, max_length=255)
    idempotency_key: str = Field(min_length=1, max_length=255)


class CallToolCommand(RemoteModel):
    """Transport-neutral command that invokes one task tool."""

    run_id: str = Field(min_length=1, max_length=255)
    task_id: str = Field(min_length=1, max_length=255)
    call_id: str = Field(min_length=1, max_length=255)
    tool_name: str = Field(min_length=1, max_length=255)
    arguments: dict[str, Any] = Field(default_factory=dict)


class AbortTaskCommand(RemoteModel):
    """Transport-neutral command that aborts one task."""

    ERROR_MESSAGE_MAX_LENGTH: ClassVar[int] = 4096

    run_id: str = Field(min_length=1, max_length=255)
    task_id: str = Field(min_length=1, max_length=255)
    idempotency_key: str = Field(min_length=1, max_length=255)
    error_message: str | None = Field(default=None, max_length=ERROR_MESSAGE_MAX_LENGTH)

    @field_validator("error_message", mode="before")
    @classmethod
    def truncate_error_message(cls, error_message: Any) -> Any:
        """
        Truncate an optional diagnostic to the public protocol limit.

        Args:
            error_message: Candidate diagnostic supplied by the caller.

        Returns:
            Diagnostic bounded to the configured maximum length.

        """
        if isinstance(error_message, str):
            return error_message[: cls.ERROR_MESSAGE_MAX_LENGTH]
        return error_message


class CloseRunCommand(RemoteModel):
    """Transport-neutral command that closes one run."""

    ERROR_MESSAGE_MAX_LENGTH: ClassVar[int] = 4096

    run_id: str = Field(min_length=1, max_length=255)
    idempotency_key: str = Field(min_length=1, max_length=255)
    reason: CloseRunReason = "client_requested"
    error_message: str | None = Field(default=None, max_length=ERROR_MESSAGE_MAX_LENGTH)

    @field_validator("error_message", mode="before")
    @classmethod
    def truncate_error_message(cls, error_message: Any) -> Any:
        """Bound client diagnostics to the public protocol limit.

        Args:
            error_message: Candidate diagnostic supplied by the caller.

        Returns:
            Diagnostic bounded to the configured maximum length.
        """
        if isinstance(error_message, str):
            return error_message[: cls.ERROR_MESSAGE_MAX_LENGTH]
        return error_message


class RemoteRun(RemoteModel):
    """Validated public metadata for a remote run."""

    run_id: str = Field(min_length=1, max_length=255)
    state: Literal["active", "closing", "closed"]


class LeasedTask(RemoteModel):
    """A task leased for a specific run."""

    run_id: str = Field(min_length=1, max_length=255)
    task: PublicTask


class QueueExhausted(RemoteModel):
    """Explicit signal that a run has no remaining tasks."""

    run_id: str = Field(min_length=1, max_length=255)


LeaseTaskOutcome = LeasedTask | QueueExhausted


class ToolCallOutcome(RemoteModel):
    """Validated tool response with request-correlation identifiers."""

    run_id: str = Field(min_length=1, max_length=255)
    call_id: str = Field(min_length=1, max_length=255)
    result: ToolCallResult


class AbortTaskOutcome(RemoteModel):
    """Validated abort response with its run identifier."""

    run_id: str = Field(min_length=1, max_length=255)
    task_result: TaskResult


class CloseRunOutcome(RemoteModel):
    """Validated result of closing a run."""

    run_id: str = Field(min_length=1, max_length=255)
    state: Literal["closing", "closed"]


def _validate_dynamic_object(
    value: dict[str, Any],
    *,
    limits: DynamicValueLimits,
) -> None:
    """
    Validate a canonical recursive object without using a wire transport.

    Args:
        value: Candidate top-level object.
        limits: Recursive value bounds.

    Raises:
        ValueError: If the object contains unsupported or oversized values.

    """
    count = [0]
    _validate_nested_object(value, depth=0, count=count, limits=limits)


def _validate_nested_object(
    value: dict[str, Any],
    *,
    depth: int,
    count: list[int],
    limits: DynamicValueLimits,
) -> None:
    """
    Validate one nested canonical object.

    Args:
        value: Object being validated.
        depth: Current recursive depth.
        count: Mutable collection-entry count.
        limits: Recursive value bounds.

    Raises:
        ValueError: If the object violates the canonical contract.

    """
    if depth > limits.max_depth:
        raise ValueError("dynamic object exceeds the configured depth limit")
    count[0] += len(value)
    if count[0] > limits.max_collection_items:
        raise ValueError("dynamic object has too many collection entries")
    for key, nested_value in value.items():
        if not isinstance(key, str):
            raise ValueError("dynamic object keys must be strings")
        _validate_dynamic_string(key, limits=limits)
        _validate_dynamic_value(
            nested_value,
            depth=depth + 1,
            count=count,
            limits=limits,
        )


def _validate_dynamic_value(
    value: Any,
    *,
    depth: int,
    count: list[int],
    limits: DynamicValueLimits,
) -> None:
    """
    Validate one nested canonical value.

    Args:
        value: Value being validated.
        depth: Current recursive depth.
        count: Mutable collection-entry count.
        limits: Recursive value bounds.

    Raises:
        ValueError: If the value violates the canonical contract.

    """
    if depth > limits.max_depth:
        raise ValueError("dynamic value exceeds the configured depth limit")
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if value < -(2**63) or value > 2**63 - 1:
            raise ValueError("dynamic integers must fit signed 64-bit range")
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("dynamic floating-point values must be finite")
        return
    if isinstance(value, str):
        _validate_dynamic_string(value, limits=limits)
        return
    if isinstance(value, dict):
        _validate_nested_object(value, depth=depth, count=count, limits=limits)
        return
    if isinstance(value, list):
        count[0] += len(value)
        if count[0] > limits.max_collection_items:
            raise ValueError("dynamic value has too many collection entries")
        for nested_value in value:
            _validate_dynamic_value(
                nested_value,
                depth=depth + 1,
                count=count,
                limits=limits,
            )
        return
    raise ValueError(
        "dynamic values support only null, bool, signed int64, finite float, string, list, "
        "and string-keyed objects"
    )


def _validate_dynamic_string(value: str, *, limits: DynamicValueLimits) -> None:
    """
    Validate one UTF-8 string against the configured size bound.

    Args:
        value: String value or object key.
        limits: Recursive value bounds.

    Raises:
        ValueError: If the encoded value is oversized.

    """
    if len(value.encode("utf-8")) > limits.max_string_bytes:
        raise ValueError("dynamic string exceeds the configured size limit")
