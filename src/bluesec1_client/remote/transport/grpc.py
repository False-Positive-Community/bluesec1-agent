import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import grpc
from google.rpc import error_details_pb2
from grpc_status import rpc_status
from loguru import logger

from ...errors import (
    IdempotencyCapacityExceededError,
    OperationCapacityExceededError,
    RunCapacityExceededError,
    TaskAlreadyFinishedError,
    TaskCapacityExceededError,
    TaskNotFoundError,
)
from ...proto.investigation.runtime.v1 import runtime_pb2_grpc
from ..errors import (
    CompetitionClosedError,
    RemoteAuthenticationError,
    RemoteAuthorizationError,
    RemoteClientError,
    RemoteClientStateError,
    RemoteConflictError,
    RemoteProtocolError,
    RemoteRateLimitError,
    RemoteRequestError,
    RemoteRunNotFoundError,
    RemoteServerError,
    RemoteSessionLostError,
    RemoteTransportError,
    RemoteUnavailableError,
)
from ..models import (
    AbortTaskCommand,
    AbortTaskOutcome,
    CallToolCommand,
    CloseRunCommand,
    CloseRunOutcome,
    CreateRunCommand,
    DeadlinePolicy,
    DynamicValueLimits,
    LeaseTaskCommand,
    LeaseTaskOutcome,
    RemoteRun,
    RetryPolicy,
    ToolCallOutcome,
)
from .base import RemoteTransport
from .mappers import (
    DynamicValueCodec,
    decode_abort_task,
    decode_close_run,
    decode_lease_task,
    decode_run,
    decode_tool_call,
    encode_abort_task,
    encode_call_tool,
    encode_close_run,
    encode_create_run,
    encode_lease_task,
)

_RATE_LIMIT_REASONS = {
    "RATE_LIMITED",
    "SUBJECT_RUN_START_RATE_LIMIT_REACHED",
}

_RUN_CAPACITY_REASONS = {
    "SUBJECT_ACTIVE_RUN_LIMIT_REACHED",
    "PROCESS_ACTIVE_RUN_LIMIT_REACHED",
}
_TASK_CAPACITY_REASONS = {
    "SUBJECT_ACTIVE_TASK_LIMIT_REACHED",
    "RUN_ACTIVE_TASK_LIMIT_REACHED",
    "PROCESS_ACTIVE_TASK_LIMIT_REACHED",
}
_OPERATION_CAPACITY_REASONS = {
    "PROCESS_IN_FLIGHT_OPERATION_LIMIT_REACHED",
    "SUBJECT_IN_FLIGHT_OPERATION_LIMIT_REACHED",
    "PROCESS_CLOSE_IN_FLIGHT_OPERATION_LIMIT_REACHED",
    "SUBJECT_CLOSE_IN_FLIGHT_OPERATION_LIMIT_REACHED",
}
_IDEMPOTENCY_CAPACITY_REASONS = {
    "PROCESS_IDEMPOTENCY_ENTRY_LIMIT_REACHED",
    "SUBJECT_IDEMPOTENCY_ENTRY_LIMIT_REACHED",
    "PROCESS_CLOSE_IDEMPOTENCY_ENTRY_LIMIT_REACHED",
    "SUBJECT_CLOSE_IDEMPOTENCY_ENTRY_LIMIT_REACHED",
}
_MAX_STATUS_BYTES = 16_384
_MAX_ERROR_DETAILS = 16
_MAX_REASON_LENGTH = 128
_MAX_REQUEST_ID_LENGTH = 255


class GrpcErrorDetails:
    """Bounded sanitized fields parsed from a rich gRPC status."""

    def __init__(
        self,
        *,
        reason: str | None = None,
        request_id: str | None = None,
        retry_after_seconds: float | None = None,
    ) -> None:
        """
        Store safe status metadata without retaining wire objects.

        Args:
            reason: Stable error reason.
            request_id: Opaque request identifier.
            retry_after_seconds: Valid bounded retry hint.

        """
        self.reason = reason
        self.request_id = request_id
        self.retry_after_seconds = retry_after_seconds


class GrpcRemoteTransport(RemoteTransport):
    """Asynchronous gRPC adapter for the versioned scenario-runtime service."""

    def __init__(
        self,
        *,
        endpoint: str,
        token: str,
        deadlines: DeadlinePolicy | None = None,
        retry_policy: RetryPolicy | None = None,
        value_limits: DynamicValueLimits | None = None,
        verify_tls: bool = True,
        root_certificates: bytes | None = None,
        channel: grpc.aio.Channel | None = None,
        stub: Any | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        """
        Configure the bounded gRPC transport.

        Args:
            endpoint: gRPC target such as `runtime.example:443` or `dns:///runtime:443`.
            token: Bearer credential attached to every public runtime RPC.
            deadlines: Per-operation deadline policy.
            retry_policy: SDK-owned bounded retry policy.
            value_limits: Canonical value and message bounds.
            verify_tls: Whether to create a TLS-verifying channel.
            root_certificates: Optional PEM roots for a TLS channel.
            channel: Caller-owned asynchronous channel for tests or custom composition.
            stub: Caller-provided generated-compatible stub.
            sleep: Injectable asynchronous backoff function.

        Raises:
            ValueError: If injected resources or TLS settings conflict.

        """
        if stub is not None and channel is not None:
            raise ValueError("inject either a channel or a stub, not both")
        if not verify_tls and root_certificates is not None:
            raise ValueError("root certificates cannot be used when TLS verification is disabled")
        self._endpoint = endpoint
        self._metadata = (("authorization", f"Bearer {token}"),)
        self._deadlines = deadlines or DeadlinePolicy()
        self._retry_policy = retry_policy or RetryPolicy()
        self._value_limits = value_limits or DynamicValueLimits()
        self._codec = DynamicValueCodec(self._value_limits)
        self._sleep = sleep
        self._closed = False
        self._owns_channel = channel is None and stub is None
        if stub is not None:
            self._channel = None
            self._stub = stub
        else:
            self._channel = channel or self._create_channel(
                endpoint=endpoint,
                verify_tls=verify_tls,
                root_certificates=root_certificates,
            )
            self._stub = runtime_pb2_grpc.ScenarioRuntimeStub(self._channel)

    def __repr__(self) -> str:
        """
        Return a representation that never contains the bearer token.

        Returns:
            Sanitized transport representation.

        """
        return f"GrpcRemoteTransport(endpoint={self._endpoint!r}, closed={self._closed!r})"

    async def create_run(self, command: CreateRunCommand) -> RemoteRun:
        """
        Create and validate a new remote run.

        Args:
            command: Idempotent run-creation command.

        Returns:
            Created run metadata.

        """
        request = encode_create_run(command, self._codec)
        response = await self._invoke(
            self._stub.CreateRun,
            request,
            deadline=self._deadlines.create_run,
            idempotent=True,
            operation="CreateRun",
        )
        self._codec.ensure_message_size(response, response=True)
        return decode_run(response)

    async def lease_task(self, command: LeaseTaskCommand) -> LeaseTaskOutcome:
        """
        Lease and validate a task or explicit queue exhaustion.

        Args:
            command: Idempotent task-lease command.

        Returns:
            Leased task or queue-exhaustion outcome.

        """
        request = encode_lease_task(command)
        response = await self._invoke(
            self._stub.LeaseTask,
            request,
            deadline=self._deadlines.lease_task,
            idempotent=True,
            operation="LeaseTask",
        )
        return decode_lease_task(response, command, self._codec)

    async def call_tool(self, command: CallToolCommand) -> ToolCallOutcome:
        """
        Invoke a tool and validate its correlated public result.

        Args:
            command: Correlated tool-call command.

        Returns:
            Correlated public tool result.

        """
        request = encode_call_tool(command, self._codec)
        response = await self._invoke(
            self._stub.CallTool,
            request,
            deadline=self._deadlines.call_tool,
            idempotent=True,
            operation="CallTool",
        )
        return decode_tool_call(response, command, self._codec)

    async def abort_task(self, command: AbortTaskCommand) -> AbortTaskOutcome:
        """
        Abort a task and validate its terminal public result.

        Args:
            command: Idempotent task-abort command.

        Returns:
            Correlated terminal result.

        """
        request = encode_abort_task(command)
        response = await self._invoke(
            self._stub.AbortTask,
            request,
            deadline=self._deadlines.abort_task,
            idempotent=True,
            operation="AbortTask",
        )
        self._codec.ensure_message_size(response, response=True)
        return decode_abort_task(response, command)

    async def close_run(self, command: CloseRunCommand) -> CloseRunOutcome:
        """
        Close a run and validate its terminal lifecycle state.

        Args:
            command: Idempotent run-close command.

        Returns:
            Closing or closed run outcome.

        """
        request = encode_close_run(command)
        response = await self._invoke(
            self._stub.CloseRun,
            request,
            deadline=self._deadlines.close_run,
            idempotent=True,
            operation="CloseRun",
        )
        self._codec.ensure_message_size(response, response=True)
        return decode_close_run(response, command)

    async def aclose(self) -> None:
        """Close the SDK-owned channel within the configured deadline."""
        if self._closed:
            return
        self._closed = True
        if not self._owns_channel or self._channel is None:
            return
        try:
            await asyncio.wait_for(
                self._channel.close(grace=self._deadlines.channel_close),
                timeout=self._deadlines.channel_close + 3.0,
            )
        except TimeoutError:
            logger.warning("Timed out while closing the owned remote runtime channel")

    async def _invoke(
        self,
        method: Any,
        request: Any,
        *,
        deadline: float,
        idempotent: bool,
        operation: str,
    ) -> Any:
        """
        Invoke one RPC using the single bounded SDK retry loop.

        Args:
            method: Generated-compatible unary RPC callable.
            request: Encoded Protobuf request.
            deadline: Deadline applied independently to each attempt.
            idempotent: Whether deadline failures may be retried safely.
            operation: Safe RPC operation name for logs.

        Returns:
            Protobuf response.

        Raises:
            RemoteClientError: If the mapped remote failure exhausts or forbids retry.

        """
        if self._closed:
            raise RemoteClientStateError("The remote transport is closed.")
        for attempt in range(1, self._retry_policy.max_attempts + 1):
            try:
                logger.debug(f"Remote RPC attempt: operation={operation} attempt={attempt}")
                return await method(
                    request,
                    timeout=deadline,
                    metadata=self._metadata,
                    wait_for_ready=False,
                )
            except grpc.aio.AioRpcError as exc:
                mapped = map_grpc_error(
                    exc,
                    retry_policy=self._retry_policy,
                    idempotent=idempotent,
                )
                if not isinstance(mapped, RemoteClientError):
                    raise mapped from None
                if not mapped.retryable or attempt >= self._retry_policy.max_attempts:
                    raise mapped from None
                delay = mapped.retry_after_seconds
                if delay is None:
                    delay = min(
                        self._retry_policy.initial_backoff_seconds
                        * self._retry_policy.backoff_multiplier ** (attempt - 1),
                        self._retry_policy.max_backoff_seconds,
                    )
                await self._sleep(delay)
        raise RemoteTransportError("The remote request exhausted its retry budget.")

    def _create_channel(
        self,
        *,
        endpoint: str,
        verify_tls: bool,
        root_certificates: bytes | None,
    ) -> grpc.aio.Channel:
        """
        Create an SDK-owned channel with built-in retries disabled.

        Args:
            endpoint: gRPC target passed to channel construction.
            verify_tls: Whether to enable TLS verification.
            root_certificates: Optional PEM trust roots.

        Returns:
            New asynchronous channel.

        """
        message_limit = self._value_limits.grpc_message_bytes
        options = (
            ("grpc.enable_retries", 0),
            ("grpc.max_send_message_length", message_limit),
            ("grpc.max_receive_message_length", message_limit),
            ("grpc.max_metadata_size", _MAX_STATUS_BYTES),
            ("grpc.keepalive_time_ms", 60_000),
            ("grpc.keepalive_timeout_ms", 10_000),
        )
        if verify_tls:
            credentials = grpc.ssl_channel_credentials(root_certificates=root_certificates)
            return grpc.aio.secure_channel(endpoint, credentials, options=options)
        return grpc.aio.insecure_channel(endpoint, options=options)


def map_grpc_error(
    error: grpc.aio.AioRpcError,
    *,
    retry_policy: RetryPolicy,
    idempotent: bool,
) -> Exception:
    """
    Translate a raw gRPC failure into one sanitized public SDK error.

    Args:
        error: Raw asynchronous gRPC failure.
        retry_policy: Bounds applied while parsing retry hints.
        idempotent: Whether a deadline failure can be retried safely.

    Returns:
        Sanitized SDK exception.

    """
    details = _parse_error_details(error, retry_policy=retry_policy)
    reason = details.reason
    code = error.code()
    match code, reason:
        case grpc.StatusCode.UNAUTHENTICATED, _:
            return RemoteAuthenticationError(
                "Remote runtime authentication failed.",
                reason=reason,
                request_id=details.request_id,
            )
        case grpc.StatusCode.PERMISSION_DENIED, _:
            return RemoteAuthorizationError(
                "Remote runtime authorization failed.",
                reason=reason,
                request_id=details.request_id,
            )
        case (grpc.StatusCode.UNIMPLEMENTED, _) | (_, "INCOMPATIBLE_PROTOCOL"):
            return RemoteProtocolError(
                "The runtime protocol is incompatible.",
                reason=reason,
                request_id=details.request_id,
            )
        case _, "TASK_ALREADY_FINISHED":
            return TaskAlreadyFinishedError("The remote task has already finished.")
        case (grpc.StatusCode.ALREADY_EXISTS, _) | (_, "IDEMPOTENCY_CONFLICT"):
            return RemoteConflictError(
                "The remote request conflicts with an earlier request.",
                reason=reason,
                request_id=details.request_id,
            )
        case grpc.StatusCode.NOT_FOUND, "TASK_NOT_FOUND":
            return TaskNotFoundError("The remote task could not be found.")
        case grpc.StatusCode.NOT_FOUND, "RUN_NOT_FOUND":
            return RemoteRunNotFoundError(
                "The remote run could not be found.",
                reason=reason,
                request_id=details.request_id,
            )
        case grpc.StatusCode.NOT_FOUND, _:
            return RemoteProtocolError(
                "The runtime omitted the not-found entity reason.",
                reason=reason,
                request_id=details.request_id,
            )
        case grpc.StatusCode.FAILED_PRECONDITION, "COMPETITION_ARENA_CLOSED":
            return CompetitionClosedError(
                "The competition is not accepting runs right now.",
                reason=reason,
                request_id=details.request_id,
            )
        case grpc.StatusCode.FAILED_PRECONDITION, _:
            return RemoteSessionLostError(
                "The remote runtime session is no longer active.",
                reason=reason,
                request_id=details.request_id,
            )
        case grpc.StatusCode.INVALID_ARGUMENT, _:
            return RemoteRequestError(
                "The remote runtime rejected the request.",
                reason=reason,
                request_id=details.request_id,
            )
        case grpc.StatusCode.RESOURCE_EXHAUSTED, capacity_reason if (
            capacity_reason in _RUN_CAPACITY_REASONS
        ):
            return RunCapacityExceededError(
                "Remote run capacity has been reached.",
                reason=capacity_reason,
            )
        case grpc.StatusCode.RESOURCE_EXHAUSTED, capacity_reason if (
            capacity_reason in _TASK_CAPACITY_REASONS
        ):
            return TaskCapacityExceededError(
                "Remote task capacity has been reached.",
                reason=capacity_reason,
            )
        case grpc.StatusCode.RESOURCE_EXHAUSTED, capacity_reason if (
            capacity_reason in _OPERATION_CAPACITY_REASONS
        ):
            return OperationCapacityExceededError(
                "Remote operation capacity has been reached.",
                reason=capacity_reason,
            )
        case grpc.StatusCode.RESOURCE_EXHAUSTED, capacity_reason if (
            capacity_reason in _IDEMPOTENCY_CAPACITY_REASONS
        ):
            return IdempotencyCapacityExceededError(
                "Remote idempotency capacity has been reached.",
                reason=capacity_reason,
            )
        case grpc.StatusCode.RESOURCE_EXHAUSTED, _ if (
            reason in _RATE_LIMIT_REASONS and details.retry_after_seconds is not None
        ):
            return RemoteRateLimitError(
                "The remote runtime rate limit has been reached.",
                retryable=True,
                retry_after_seconds=details.retry_after_seconds,
                reason=reason,
                request_id=details.request_id,
            )
        case grpc.StatusCode.RESOURCE_EXHAUSTED, _ if reason in _RATE_LIMIT_REASONS:
            return RemoteRateLimitError(
                "The remote runtime rate limit has been reached.",
                reason=reason,
                request_id=details.request_id,
            )
        case grpc.StatusCode.RESOURCE_EXHAUSTED, _:
            return RemoteProtocolError(
                "The runtime returned an unknown resource-exhaustion reason.",
                reason=reason,
                request_id=details.request_id,
            )
        case grpc.StatusCode.UNAVAILABLE, _:
            return RemoteUnavailableError(
                "The remote runtime is temporarily unavailable.",
                retryable=True,
                reason=reason,
                request_id=details.request_id,
            )
        case grpc.StatusCode.DEADLINE_EXCEEDED, _:
            return RemoteTransportError(
                "The remote runtime request timed out.",
                retryable=idempotent,
                reason=reason,
                request_id=details.request_id,
            )
        case grpc.StatusCode.CANCELLED, _:
            return RemoteTransportError(
                "The remote runtime connection failed.",
                reason=reason,
                request_id=details.request_id,
            )
        case _:
            return RemoteServerError(
                "The remote runtime failed to process the request.",
                reason=reason,
                request_id=details.request_id,
            )


def _parse_error_details(
    error: grpc.aio.AioRpcError,
    *,
    retry_policy: RetryPolicy,
) -> GrpcErrorDetails:
    """
    Parse supported rich-error details under strict size and count bounds.

    Args:
        error: Raw asynchronous gRPC failure.
        retry_policy: Bound for accepted retry delays.

    Returns:
        Sanitized error metadata; malformed details are ignored.

    """
    try:
        status_message = rpc_status.from_call(error)
        if status_message is None or status_message.ByteSize() > _MAX_STATUS_BYTES:
            return GrpcErrorDetails()
    except (AttributeError, TypeError, ValueError):
        return GrpcErrorDetails()
    reason: str | None = None
    request_id: str | None = None
    retry_after_seconds: float | None = None
    for packed_detail in status_message.details[:_MAX_ERROR_DETAILS]:
        if packed_detail.Is(error_details_pb2.ErrorInfo.DESCRIPTOR):
            error_info = error_details_pb2.ErrorInfo()
            if (
                packed_detail.Unpack(error_info)
                and 0 < len(error_info.reason) <= _MAX_REASON_LENGTH
            ):
                reason = error_info.reason
        elif packed_detail.Is(error_details_pb2.RequestInfo.DESCRIPTOR):
            request_info = error_details_pb2.RequestInfo()
            if (
                packed_detail.Unpack(request_info)
                and 0 < len(request_info.request_id) <= _MAX_REQUEST_ID_LENGTH
            ):
                request_id = request_info.request_id
        elif packed_detail.Is(error_details_pb2.RetryInfo.DESCRIPTOR):
            retry_info = error_details_pb2.RetryInfo()
            if packed_detail.Unpack(retry_info):
                retry_after_seconds = _parse_retry_delay(
                    retry_info,
                    max_seconds=retry_policy.max_retry_after_seconds,
                )
    return GrpcErrorDetails(
        reason=reason,
        request_id=request_id,
        retry_after_seconds=retry_after_seconds,
    )


def _parse_retry_delay(
    retry_info: error_details_pb2.RetryInfo,
    *,
    max_seconds: float,
) -> float | None:
    """
    Parse a non-negative bounded retry delay.

    Args:
        retry_info: Standard rich-error retry detail.
        max_seconds: Maximum accepted delay.

    Returns:
        Delay in seconds, or `None` when invalid.

    """
    if not retry_info.HasField("retry_delay"):
        return None
    seconds = retry_info.retry_delay.seconds
    nanos = retry_info.retry_delay.nanos
    if seconds < 0 or nanos < 0 or nanos >= 1_000_000_000:
        return None
    delay = seconds + nanos / 1_000_000_000
    if delay > max_seconds:
        return None
    return delay
