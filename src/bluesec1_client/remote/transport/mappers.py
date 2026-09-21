import math
from typing import Any, Literal

from google.protobuf import struct_pb2
from pydantic import ValidationError

from ...proto.investigation.runtime.v1 import runtime_pb2
from ...protocols import PublicTask, TaskResult, ToolCallResult
from ..errors import RemoteProtocolError, RemoteRequestError
from ..models import (
    AbortTaskCommand,
    AbortTaskOutcome,
    CallToolCommand,
    CloseRunCommand,
    CloseRunOutcome,
    CreateRunCommand,
    DynamicValueLimits,
    LeasedTask,
    LeaseTaskCommand,
    LeaseTaskOutcome,
    QueueExhausted,
    RemoteRun,
    ToolCallOutcome,
)

_MIN_INT64 = -(2**63)
_MAX_INT64 = 2**63 - 1


class DynamicValueCodec:
    """Encode and decode bounded canonical recursive values."""

    def __init__(self, limits: DynamicValueLimits) -> None:
        """
        Configure value validation bounds.

        Args:
            limits: Maximum depth, collection size, string size, and message size.

        """
        self._limits = limits

    def encode_object(self, value: dict[str, Any]) -> runtime_pb2.DynamicObject:
        """
        Encode a top-level canonical object.

        Args:
            value: Python object containing canonical tool values.

        Returns:
            Encoded Protobuf dynamic object.

        Raises:
            RemoteRequestError: If the value is unsupported or exceeds a bound.

        """
        counter = [0]
        return self._encode_object(value, depth=0, counter=counter)

    def decode_object(self, value: runtime_pb2.DynamicObject) -> dict[str, Any]:
        """
        Decode a Protobuf dynamic object into canonical Python values.

        Args:
            value: Protobuf object returned by the runtime.

        Returns:
            Canonical Python object.

        Raises:
            RemoteProtocolError: If the value is malformed or exceeds a bound.

        """
        counter = [0]
        return self._decode_object(value, depth=0, counter=counter)

    def ensure_message_size(self, message: Any, *, response: bool) -> None:
        """
        Reject a serialized request or response above the configured bound.

        Args:
            message: Protobuf message exposing `ByteSize()`.
            response: Whether the message came from the server.

        Raises:
            RemoteProtocolError: If a response is oversized.
            RemoteRequestError: If a request is oversized.

        """
        try:
            message_size = int(message.ByteSize())
        except (AttributeError, TypeError, ValueError) as exc:
            if response:
                raise RemoteProtocolError("The runtime returned an invalid response.") from exc
            raise RemoteRequestError("The remote request could not be encoded.") from exc
        if message_size <= self._limits.max_message_bytes:
            return
        if response:
            raise RemoteProtocolError("The runtime response exceeds the configured size limit.")
        raise RemoteRequestError("The remote request exceeds the configured size limit.")

    def _encode_object(
        self,
        value: dict[str, Any],
        *,
        depth: int,
        counter: list[int],
    ) -> runtime_pb2.DynamicObject:
        """
        Encode one canonical object recursively.

        Args:
            value: Object to encode.
            depth: Current recursive depth.
            counter: Mutable count of collection entries.

        Returns:
            Encoded object.

        """
        self._validate_depth(depth, response=False)
        self._count_items(len(value), counter=counter, response=False)
        encoded = runtime_pb2.DynamicObject()
        for key, nested_value in value.items():
            if not isinstance(key, str):
                raise RemoteRequestError("Tool argument object keys must be strings.")
            self._validate_string(key, response=False)
            encoded.fields[key].CopyFrom(
                self._encode_value(nested_value, depth=depth + 1, counter=counter)
            )
        return encoded

    def _encode_value(
        self,
        value: Any,
        *,
        depth: int,
        counter: list[int],
    ) -> runtime_pb2.DynamicValue:
        """
        Encode one canonical value recursively.

        Args:
            value: Value to encode.
            depth: Current recursive depth.
            counter: Mutable count of collection entries.

        Returns:
            Encoded value.

        """
        self._validate_depth(depth, response=False)
        if value is None:
            return runtime_pb2.DynamicValue(null_value=struct_pb2.NULL_VALUE)
        if isinstance(value, bool):
            return runtime_pb2.DynamicValue(bool_value=value)
        if isinstance(value, int):
            if value < _MIN_INT64 or value > _MAX_INT64:
                raise RemoteRequestError("Integer tool arguments must fit signed 64-bit range.")
            return runtime_pb2.DynamicValue(integer_value=value)
        if isinstance(value, float):
            if not math.isfinite(value):
                raise RemoteRequestError("Floating-point tool arguments must be finite.")
            return runtime_pb2.DynamicValue(float_value=value)
        if isinstance(value, str):
            self._validate_string(value, response=False)
            return runtime_pb2.DynamicValue(string_value=value)
        if isinstance(value, dict):
            return runtime_pb2.DynamicValue(
                object_value=self._encode_object(value, depth=depth, counter=counter)
            )
        if isinstance(value, list):
            self._count_items(len(value), counter=counter, response=False)
            return runtime_pb2.DynamicValue(
                list_value=runtime_pb2.DynamicList(
                    values=[
                        self._encode_value(nested, depth=depth + 1, counter=counter)
                        for nested in value
                    ]
                )
            )
        raise RemoteRequestError(
            "Tool arguments support only null, bool, signed int64, finite float, string, list, "
            "and string-keyed object values."
        )

    def _decode_object(
        self,
        value: runtime_pb2.DynamicObject,
        *,
        depth: int,
        counter: list[int],
    ) -> dict[str, Any]:
        """
        Decode one Protobuf object recursively.

        Args:
            value: Object to decode.
            depth: Current recursive depth.
            counter: Mutable count of collection entries.

        Returns:
            Decoded canonical object.

        """
        self._validate_depth(depth, response=True)
        self._count_items(len(value.fields), counter=counter, response=True)
        decoded: dict[str, Any] = {}
        for key, nested_value in value.fields.items():
            self._validate_string(key, response=True)
            decoded[key] = self._decode_value(
                nested_value,
                depth=depth + 1,
                counter=counter,
            )
        return decoded

    def _decode_value(
        self,
        value: runtime_pb2.DynamicValue,
        *,
        depth: int,
        counter: list[int],
    ) -> Any:
        """
        Decode one Protobuf value recursively.

        Args:
            value: Value to decode.
            depth: Current recursive depth.
            counter: Mutable count of collection entries.

        Returns:
            Decoded canonical value.

        Raises:
            RemoteProtocolError: If the Protobuf oneof is unset or invalid.

        """
        self._validate_depth(depth, response=True)
        kind = value.WhichOneof("kind")
        if kind == "null_value":
            return None
        if kind == "bool_value":
            return value.bool_value
        if kind == "integer_value":
            return value.integer_value
        if kind == "float_value":
            if not math.isfinite(value.float_value):
                raise RemoteProtocolError("The runtime returned a non-finite floating-point value.")
            return value.float_value
        if kind == "string_value":
            self._validate_string(value.string_value, response=True)
            return value.string_value
        if kind == "object_value":
            return self._decode_object(value.object_value, depth=depth, counter=counter)
        if kind == "list_value":
            self._count_items(len(value.list_value.values), counter=counter, response=True)
            return [
                self._decode_value(nested, depth=depth + 1, counter=counter)
                for nested in value.list_value.values
            ]
        raise RemoteProtocolError("The runtime returned an unset dynamic value.")

    def _validate_depth(self, depth: int, *, response: bool) -> None:
        """
        Enforce the recursive depth bound.

        Args:
            depth: Current recursive depth.
            response: Whether the value came from the server.

        Raises:
            RemoteProtocolError: If a response exceeds the bound.
            RemoteRequestError: If a request exceeds the bound.

        """
        if depth <= self._limits.max_depth:
            return
        if response:
            raise RemoteProtocolError("The runtime response exceeds the configured depth limit.")
        raise RemoteRequestError("Tool arguments exceed the configured depth limit.")

    def _count_items(self, count: int, *, counter: list[int], response: bool) -> None:
        """
        Add entries to the bounded collection-item count.

        Args:
            count: Number of entries in the current collection.
            counter: Mutable total count.
            response: Whether the value came from the server.

        Raises:
            RemoteProtocolError: If a response exceeds the bound.
            RemoteRequestError: If a request exceeds the bound.

        """
        counter[0] += count
        if counter[0] <= self._limits.max_collection_items:
            return
        if response:
            raise RemoteProtocolError("The runtime response has too many collection entries.")
        raise RemoteRequestError("Tool arguments have too many collection entries.")

    def _validate_string(self, value: str, *, response: bool) -> None:
        """
        Enforce the UTF-8 string-size bound.

        Args:
            value: String value or object key.
            response: Whether the string came from the server.

        Raises:
            RemoteProtocolError: If a response exceeds the bound.
            RemoteRequestError: If a request exceeds the bound.

        """
        if len(value.encode("utf-8")) <= self._limits.max_string_bytes:
            return
        if response:
            raise RemoteProtocolError("The runtime response contains an oversized string.")
        raise RemoteRequestError("Tool arguments contain an oversized string.")


def encode_create_run(
    command: CreateRunCommand,
    codec: DynamicValueCodec,
) -> runtime_pb2.CreateRunRequest:
    """
    Encode a run-creation command.

    Args:
        command: Transport-neutral command.
        codec: Canonical value codec.

    Returns:
        Protobuf request.

    """
    request = runtime_pb2.CreateRunRequest(
        idempotency_key=command.idempotency_key,
        metadata=codec.encode_object(command.metadata),
    )
    if command.label is not None:
        request.label = command.label
    if command.agent_name is not None:
        request.agent_name = command.agent_name
    if command.model_name is not None:
        request.model_name = command.model_name
    if command.arena is not None:
        request.arena = command.arena
    codec.ensure_message_size(request, response=False)
    return request


def decode_run(response: runtime_pb2.Run) -> RemoteRun:
    """
    Decode validated remote run metadata.

    Args:
        response: Protobuf run response.

    Returns:
        Transport-neutral run metadata.

    Raises:
        RemoteProtocolError: If required fields or enum semantics are invalid.

    """
    states: dict[int, Literal["active", "closing", "closed"]] = {
        runtime_pb2.RUN_STATE_ACTIVE: "active",
        runtime_pb2.RUN_STATE_CLOSING: "closing",
        runtime_pb2.RUN_STATE_CLOSED: "closed",
    }
    state = states.get(response.state)
    if state is None or not response.run_id:
        raise RemoteProtocolError("The runtime returned invalid run metadata.")
    try:
        return RemoteRun(
            run_id=response.run_id,
            state=state,
        )
    except ValidationError:
        raise RemoteProtocolError("The runtime returned invalid run metadata.") from None


def encode_lease_task(command: LeaseTaskCommand) -> runtime_pb2.LeaseTaskRequest:
    """
    Encode a task-lease command.

    Args:
        command: Transport-neutral command.

    Returns:
        Protobuf request.

    """
    return runtime_pb2.LeaseTaskRequest(
        run_id=command.run_id,
        idempotency_key=command.idempotency_key,
    )


def decode_lease_task(
    response: runtime_pb2.LeaseTaskResponse,
    command: LeaseTaskCommand,
    codec: DynamicValueCodec,
) -> LeaseTaskOutcome:
    """
    Decode and correlate a task-lease response.

    Args:
        response: Protobuf response.
        command: Original lease command.
        codec: Canonical value codec.

    Returns:
        Leased task or explicit exhaustion.

    Raises:
        RemoteProtocolError: If the outcome or identifiers are invalid.

    """
    codec.ensure_message_size(response, response=True)
    outcome = response.WhichOneof("outcome")
    if outcome == "exhausted":
        if response.exhausted.run_id != command.run_id:
            raise RemoteProtocolError("The runtime returned a mismatched run identifier.")
        return QueueExhausted(run_id=response.exhausted.run_id)
    if outcome != "leased":
        raise RemoteProtocolError("The runtime returned an invalid task-lease outcome.")
    leased = response.leased
    if (
        leased.run_id != command.run_id
        or not leased.HasField("task")
        or not leased.task.task_id
        or len(leased.task.task_id) > 255
    ):
        raise RemoteProtocolError("The runtime returned an invalid leased task.")
    try:
        task = PublicTask(
            task_id=leased.task.task_id,
            observation=codec.decode_object(leased.task.observation),
        )
        return LeasedTask(run_id=leased.run_id, task=task)
    except ValidationError:
        raise RemoteProtocolError("The runtime returned an invalid leased task.") from None


def encode_call_tool(
    command: CallToolCommand,
    codec: DynamicValueCodec,
) -> runtime_pb2.CallToolRequest:
    """
    Encode a correlated tool-call command.

    Args:
        command: Transport-neutral command.
        codec: Canonical value codec.

    Returns:
        Protobuf request.

    """
    request = runtime_pb2.CallToolRequest(
        run_id=command.run_id,
        task_id=command.task_id,
        call_id=command.call_id,
        tool_name=command.tool_name,
        arguments=codec.encode_object(command.arguments),
    )
    codec.ensure_message_size(request, response=False)
    return request


def decode_tool_call(
    response: runtime_pb2.ToolCallResponse,
    command: CallToolCommand,
    codec: DynamicValueCodec,
) -> ToolCallOutcome:
    """
    Decode and correlate a public tool-call response.

    Args:
        response: Protobuf response.
        command: Original tool-call command.
        codec: Canonical value codec.

    Returns:
        Correlated public tool result.

    Raises:
        RemoteProtocolError: If identifiers or terminal semantics are invalid.

    """
    codec.ensure_message_size(response, response=True)
    if (
        response.run_id != command.run_id
        or response.task_id != command.task_id
        or response.call_id != command.call_id
        or response.tool_name != command.tool_name
    ):
        raise RemoteProtocolError("The runtime returned mismatched tool-call identifiers.")
    has_result = response.HasField("task_result")
    is_terminal = response.terminated or response.truncated
    if has_result != is_terminal or not math.isfinite(response.reward):
        raise RemoteProtocolError("The runtime returned invalid terminal tool-call state.")
    task_result = decode_task_result(response.task_result) if has_result else None
    if task_result is not None and task_result.task_id != command.task_id:
        raise RemoteProtocolError("The runtime returned a mismatched terminal task identifier.")
    if task_result is not None:
        valid_reason = (response.terminated and task_result.completion_reason == "terminated") or (
            response.truncated and task_result.completion_reason in {"truncated", "error"}
        )
        if not valid_reason:
            raise RemoteProtocolError("The runtime returned inconsistent completion semantics.")
    try:
        result = ToolCallResult(
            task_id=response.task_id,
            tool_name=response.tool_name,
            observation=codec.decode_object(response.observation),
            reward=response.reward,
            terminated=response.terminated,
            truncated=response.truncated,
            info=codec.decode_object(response.info),
            task_result=task_result,
        )
        return ToolCallOutcome(run_id=response.run_id, call_id=response.call_id, result=result)
    except ValidationError:
        raise RemoteProtocolError("The runtime returned an invalid tool result.") from None


def decode_task_result(response: runtime_pb2.TaskResult) -> TaskResult:
    """
    Decode a public terminal task result.

    Args:
        response: Protobuf task result.

    Returns:
        Public task result.

    Raises:
        RemoteProtocolError: If fields or completion semantics are invalid.

    """
    reasons: dict[int, Literal["terminated", "truncated", "error", "aborted"]] = {
        runtime_pb2.COMPLETION_REASON_TERMINATED: "terminated",
        runtime_pb2.COMPLETION_REASON_TRUNCATED: "truncated",
        runtime_pb2.COMPLETION_REASON_ERROR: "error",
        runtime_pb2.COMPLETION_REASON_ABORTED: "aborted",
    }
    reason = reasons.get(response.completion_reason)
    numeric_values = (
        response.total_reward,
        response.quality_score,
        response.efficiency_score,
        response.wall_time_seconds,
    )
    if (
        reason is None
        or not response.task_id
        or len(response.task_id) > 255
        or any(not math.isfinite(value) for value in numeric_values)
    ):
        raise RemoteProtocolError("The runtime returned an invalid task result.")
    try:
        return TaskResult(
            task_id=response.task_id,
            completion_reason=reason,
            total_reward=response.total_reward,
            steps_taken=response.steps_taken,
            tool_calls=response.tool_calls,
            quality_score=response.quality_score,
            efficiency_score=response.efficiency_score,
            wall_time_seconds=response.wall_time_seconds,
        )
    except ValidationError:
        raise RemoteProtocolError("The runtime returned an invalid task result.") from None


def encode_abort_task(command: AbortTaskCommand) -> runtime_pb2.AbortTaskRequest:
    """
    Encode an idempotent task-abort command.

    Args:
        command: Transport-neutral command.

    Returns:
        Protobuf request.

    """
    request = runtime_pb2.AbortTaskRequest(
        run_id=command.run_id,
        task_id=command.task_id,
        idempotency_key=command.idempotency_key,
    )
    if command.error_message is not None:
        request.error_message = command.error_message
    return request


def decode_abort_task(
    response: runtime_pb2.AbortTaskResponse,
    command: AbortTaskCommand,
) -> AbortTaskOutcome:
    """
    Decode and correlate a task-abort response.

    Args:
        response: Protobuf response.
        command: Original abort command.

    Returns:
        Correlated terminal task result.

    Raises:
        RemoteProtocolError: If identifiers are missing or mismatched.

    """
    if response.run_id != command.run_id or not response.HasField("task_result"):
        raise RemoteProtocolError("The runtime returned an invalid abort response.")
    task_result = decode_task_result(response.task_result)
    if task_result.task_id != command.task_id:
        raise RemoteProtocolError("The runtime returned a mismatched task identifier.")
    return AbortTaskOutcome(run_id=response.run_id, task_result=task_result)


def encode_close_run(command: CloseRunCommand) -> runtime_pb2.CloseRunRequest:
    """
    Encode an idempotent run-close command.

    Args:
        command: Transport-neutral command.

    Returns:
        Protobuf request.

    """
    reasons = {
        "client_requested": runtime_pb2.CLOSE_RUN_REASON_CLIENT_REQUESTED,
        "client_error": runtime_pb2.CLOSE_RUN_REASON_CLIENT_ERROR,
        "client_interrupted": runtime_pb2.CLOSE_RUN_REASON_CLIENT_INTERRUPTED,
    }
    request = runtime_pb2.CloseRunRequest(
        run_id=command.run_id,
        idempotency_key=command.idempotency_key,
        reason=reasons[command.reason],
    )
    if command.error_message is not None:
        request.error_message = command.error_message
    return request


def decode_close_run(
    response: runtime_pb2.CloseRunResponse,
    command: CloseRunCommand,
) -> CloseRunOutcome:
    """
    Decode and correlate a run-close response.

    Args:
        response: Protobuf response.
        command: Original close command.

    Returns:
        Closing or closed run state.

    Raises:
        RemoteProtocolError: If the identifier or state is invalid.

    """
    states: dict[int, Literal["closing", "closed"]] = {
        runtime_pb2.RUN_STATE_CLOSING: "closing",
        runtime_pb2.RUN_STATE_CLOSED: "closed",
    }
    state = states.get(response.state)
    if response.run_id != command.run_id or state is None:
        raise RemoteProtocolError("The runtime returned an invalid close response.")
    return CloseRunOutcome(run_id=response.run_id, state=state)
