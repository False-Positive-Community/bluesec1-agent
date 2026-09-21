from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class RuntimeErrorReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    RUNTIME_ERROR_REASON_UNSPECIFIED: _ClassVar[RuntimeErrorReason]
    RUN_NOT_FOUND: _ClassVar[RuntimeErrorReason]
    TASK_NOT_FOUND: _ClassVar[RuntimeErrorReason]
    IDEMPOTENCY_CONFLICT: _ClassVar[RuntimeErrorReason]
    SUBJECT_ACTIVE_TASK_LIMIT_REACHED: _ClassVar[RuntimeErrorReason]
    RUN_ACTIVE_TASK_LIMIT_REACHED: _ClassVar[RuntimeErrorReason]
    PROCESS_ACTIVE_TASK_LIMIT_REACHED: _ClassVar[RuntimeErrorReason]
    RATE_LIMITED: _ClassVar[RuntimeErrorReason]
    RUNTIME_SESSION_LOST: _ClassVar[RuntimeErrorReason]
    RUN_CLOSED: _ClassVar[RuntimeErrorReason]
    TASK_ALREADY_FINISHED: _ClassVar[RuntimeErrorReason]
    INVALID_DYNAMIC_VALUE: _ClassVar[RuntimeErrorReason]
    INCOMPATIBLE_PROTOCOL: _ClassVar[RuntimeErrorReason]
    RUNTIME_UNAVAILABLE: _ClassVar[RuntimeErrorReason]
    INTERNAL_RUNTIME_ERROR: _ClassVar[RuntimeErrorReason]
    SUBJECT_ACTIVE_RUN_LIMIT_REACHED: _ClassVar[RuntimeErrorReason]
    PROCESS_ACTIVE_RUN_LIMIT_REACHED: _ClassVar[RuntimeErrorReason]
    PROCESS_IN_FLIGHT_OPERATION_LIMIT_REACHED: _ClassVar[RuntimeErrorReason]
    SUBJECT_IN_FLIGHT_OPERATION_LIMIT_REACHED: _ClassVar[RuntimeErrorReason]
    PROCESS_IDEMPOTENCY_ENTRY_LIMIT_REACHED: _ClassVar[RuntimeErrorReason]
    SUBJECT_IDEMPOTENCY_ENTRY_LIMIT_REACHED: _ClassVar[RuntimeErrorReason]
    PROCESS_CLOSE_IN_FLIGHT_OPERATION_LIMIT_REACHED: _ClassVar[RuntimeErrorReason]
    SUBJECT_CLOSE_IN_FLIGHT_OPERATION_LIMIT_REACHED: _ClassVar[RuntimeErrorReason]
    PROCESS_CLOSE_IDEMPOTENCY_ENTRY_LIMIT_REACHED: _ClassVar[RuntimeErrorReason]
    SUBJECT_CLOSE_IDEMPOTENCY_ENTRY_LIMIT_REACHED: _ClassVar[RuntimeErrorReason]
    COMPETITION_ARENA_CLOSED: _ClassVar[RuntimeErrorReason]
    SUBJECT_RUN_START_RATE_LIMIT_REACHED: _ClassVar[RuntimeErrorReason]

class RunState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    RUN_STATE_UNSPECIFIED: _ClassVar[RunState]
    RUN_STATE_ACTIVE: _ClassVar[RunState]
    RUN_STATE_CLOSING: _ClassVar[RunState]
    RUN_STATE_CLOSED: _ClassVar[RunState]

class CloseRunReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CLOSE_RUN_REASON_UNSPECIFIED: _ClassVar[CloseRunReason]
    CLOSE_RUN_REASON_CLIENT_REQUESTED: _ClassVar[CloseRunReason]
    CLOSE_RUN_REASON_CLIENT_ERROR: _ClassVar[CloseRunReason]
    CLOSE_RUN_REASON_CLIENT_INTERRUPTED: _ClassVar[CloseRunReason]

class CompletionReason(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    COMPLETION_REASON_UNSPECIFIED: _ClassVar[CompletionReason]
    COMPLETION_REASON_TERMINATED: _ClassVar[CompletionReason]
    COMPLETION_REASON_TRUNCATED: _ClassVar[CompletionReason]
    COMPLETION_REASON_ERROR: _ClassVar[CompletionReason]
    COMPLETION_REASON_ABORTED: _ClassVar[CompletionReason]
RUNTIME_ERROR_REASON_UNSPECIFIED: RuntimeErrorReason
RUN_NOT_FOUND: RuntimeErrorReason
TASK_NOT_FOUND: RuntimeErrorReason
IDEMPOTENCY_CONFLICT: RuntimeErrorReason
SUBJECT_ACTIVE_TASK_LIMIT_REACHED: RuntimeErrorReason
RUN_ACTIVE_TASK_LIMIT_REACHED: RuntimeErrorReason
PROCESS_ACTIVE_TASK_LIMIT_REACHED: RuntimeErrorReason
RATE_LIMITED: RuntimeErrorReason
RUNTIME_SESSION_LOST: RuntimeErrorReason
RUN_CLOSED: RuntimeErrorReason
TASK_ALREADY_FINISHED: RuntimeErrorReason
INVALID_DYNAMIC_VALUE: RuntimeErrorReason
INCOMPATIBLE_PROTOCOL: RuntimeErrorReason
RUNTIME_UNAVAILABLE: RuntimeErrorReason
INTERNAL_RUNTIME_ERROR: RuntimeErrorReason
SUBJECT_ACTIVE_RUN_LIMIT_REACHED: RuntimeErrorReason
PROCESS_ACTIVE_RUN_LIMIT_REACHED: RuntimeErrorReason
PROCESS_IN_FLIGHT_OPERATION_LIMIT_REACHED: RuntimeErrorReason
SUBJECT_IN_FLIGHT_OPERATION_LIMIT_REACHED: RuntimeErrorReason
PROCESS_IDEMPOTENCY_ENTRY_LIMIT_REACHED: RuntimeErrorReason
SUBJECT_IDEMPOTENCY_ENTRY_LIMIT_REACHED: RuntimeErrorReason
PROCESS_CLOSE_IN_FLIGHT_OPERATION_LIMIT_REACHED: RuntimeErrorReason
SUBJECT_CLOSE_IN_FLIGHT_OPERATION_LIMIT_REACHED: RuntimeErrorReason
PROCESS_CLOSE_IDEMPOTENCY_ENTRY_LIMIT_REACHED: RuntimeErrorReason
SUBJECT_CLOSE_IDEMPOTENCY_ENTRY_LIMIT_REACHED: RuntimeErrorReason
COMPETITION_ARENA_CLOSED: RuntimeErrorReason
SUBJECT_RUN_START_RATE_LIMIT_REACHED: RuntimeErrorReason
RUN_STATE_UNSPECIFIED: RunState
RUN_STATE_ACTIVE: RunState
RUN_STATE_CLOSING: RunState
RUN_STATE_CLOSED: RunState
CLOSE_RUN_REASON_UNSPECIFIED: CloseRunReason
CLOSE_RUN_REASON_CLIENT_REQUESTED: CloseRunReason
CLOSE_RUN_REASON_CLIENT_ERROR: CloseRunReason
CLOSE_RUN_REASON_CLIENT_INTERRUPTED: CloseRunReason
COMPLETION_REASON_UNSPECIFIED: CompletionReason
COMPLETION_REASON_TERMINATED: CompletionReason
COMPLETION_REASON_TRUNCATED: CompletionReason
COMPLETION_REASON_ERROR: CompletionReason
COMPLETION_REASON_ABORTED: CompletionReason

class DynamicValue(_message.Message):
    __slots__ = ("null_value", "bool_value", "integer_value", "float_value", "string_value", "object_value", "list_value")
    NULL_VALUE_FIELD_NUMBER: _ClassVar[int]
    BOOL_VALUE_FIELD_NUMBER: _ClassVar[int]
    INTEGER_VALUE_FIELD_NUMBER: _ClassVar[int]
    FLOAT_VALUE_FIELD_NUMBER: _ClassVar[int]
    STRING_VALUE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_VALUE_FIELD_NUMBER: _ClassVar[int]
    LIST_VALUE_FIELD_NUMBER: _ClassVar[int]
    null_value: _struct_pb2.NullValue
    bool_value: bool
    integer_value: int
    float_value: float
    string_value: str
    object_value: DynamicObject
    list_value: DynamicList
    def __init__(self, null_value: _Optional[_Union[_struct_pb2.NullValue, str]] = ..., bool_value: _Optional[bool] = ..., integer_value: _Optional[int] = ..., float_value: _Optional[float] = ..., string_value: _Optional[str] = ..., object_value: _Optional[_Union[DynamicObject, _Mapping]] = ..., list_value: _Optional[_Union[DynamicList, _Mapping]] = ...) -> None: ...

class DynamicObject(_message.Message):
    __slots__ = ("fields",)
    class FieldsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: DynamicValue
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[DynamicValue, _Mapping]] = ...) -> None: ...
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    fields: _containers.MessageMap[str, DynamicValue]
    def __init__(self, fields: _Optional[_Mapping[str, DynamicValue]] = ...) -> None: ...

class DynamicList(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedCompositeFieldContainer[DynamicValue]
    def __init__(self, values: _Optional[_Iterable[_Union[DynamicValue, _Mapping]]] = ...) -> None: ...

class CreateRunRequest(_message.Message):
    __slots__ = ("idempotency_key", "label", "agent_name", "model_name", "metadata", "arena")
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    AGENT_NAME_FIELD_NUMBER: _ClassVar[int]
    MODEL_NAME_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    ARENA_FIELD_NUMBER: _ClassVar[int]
    idempotency_key: str
    label: str
    agent_name: str
    model_name: str
    metadata: DynamicObject
    arena: str
    def __init__(self, idempotency_key: _Optional[str] = ..., label: _Optional[str] = ..., agent_name: _Optional[str] = ..., model_name: _Optional[str] = ..., metadata: _Optional[_Union[DynamicObject, _Mapping]] = ..., arena: _Optional[str] = ...) -> None: ...

class Run(_message.Message):
    __slots__ = ("run_id", "state")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    state: RunState
    def __init__(self, run_id: _Optional[str] = ..., state: _Optional[_Union[RunState, str]] = ...) -> None: ...

class LeaseTaskRequest(_message.Message):
    __slots__ = ("run_id", "idempotency_key")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    idempotency_key: str
    def __init__(self, run_id: _Optional[str] = ..., idempotency_key: _Optional[str] = ...) -> None: ...

class PublicTask(_message.Message):
    __slots__ = ("task_id", "observation")
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    OBSERVATION_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    observation: DynamicObject
    def __init__(self, task_id: _Optional[str] = ..., observation: _Optional[_Union[DynamicObject, _Mapping]] = ...) -> None: ...

class LeasedTask(_message.Message):
    __slots__ = ("run_id", "task")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    TASK_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    task: PublicTask
    def __init__(self, run_id: _Optional[str] = ..., task: _Optional[_Union[PublicTask, _Mapping]] = ...) -> None: ...

class QueueExhausted(_message.Message):
    __slots__ = ("run_id",)
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    def __init__(self, run_id: _Optional[str] = ...) -> None: ...

class LeaseTaskResponse(_message.Message):
    __slots__ = ("leased", "exhausted")
    LEASED_FIELD_NUMBER: _ClassVar[int]
    EXHAUSTED_FIELD_NUMBER: _ClassVar[int]
    leased: LeasedTask
    exhausted: QueueExhausted
    def __init__(self, leased: _Optional[_Union[LeasedTask, _Mapping]] = ..., exhausted: _Optional[_Union[QueueExhausted, _Mapping]] = ...) -> None: ...

class CallToolRequest(_message.Message):
    __slots__ = ("run_id", "task_id", "call_id", "tool_name", "arguments")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    CALL_ID_FIELD_NUMBER: _ClassVar[int]
    TOOL_NAME_FIELD_NUMBER: _ClassVar[int]
    ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    task_id: str
    call_id: str
    tool_name: str
    arguments: DynamicObject
    def __init__(self, run_id: _Optional[str] = ..., task_id: _Optional[str] = ..., call_id: _Optional[str] = ..., tool_name: _Optional[str] = ..., arguments: _Optional[_Union[DynamicObject, _Mapping]] = ...) -> None: ...

class ToolCallResponse(_message.Message):
    __slots__ = ("run_id", "task_id", "call_id", "tool_name", "observation", "reward", "terminated", "truncated", "info", "task_result")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    CALL_ID_FIELD_NUMBER: _ClassVar[int]
    TOOL_NAME_FIELD_NUMBER: _ClassVar[int]
    OBSERVATION_FIELD_NUMBER: _ClassVar[int]
    REWARD_FIELD_NUMBER: _ClassVar[int]
    TERMINATED_FIELD_NUMBER: _ClassVar[int]
    TRUNCATED_FIELD_NUMBER: _ClassVar[int]
    INFO_FIELD_NUMBER: _ClassVar[int]
    TASK_RESULT_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    task_id: str
    call_id: str
    tool_name: str
    observation: DynamicObject
    reward: float
    terminated: bool
    truncated: bool
    info: DynamicObject
    task_result: TaskResult
    def __init__(self, run_id: _Optional[str] = ..., task_id: _Optional[str] = ..., call_id: _Optional[str] = ..., tool_name: _Optional[str] = ..., observation: _Optional[_Union[DynamicObject, _Mapping]] = ..., reward: _Optional[float] = ..., terminated: _Optional[bool] = ..., truncated: _Optional[bool] = ..., info: _Optional[_Union[DynamicObject, _Mapping]] = ..., task_result: _Optional[_Union[TaskResult, _Mapping]] = ...) -> None: ...

class TaskResult(_message.Message):
    __slots__ = ("task_id", "completion_reason", "total_reward", "steps_taken", "tool_calls", "quality_score", "efficiency_score", "wall_time_seconds")
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    COMPLETION_REASON_FIELD_NUMBER: _ClassVar[int]
    TOTAL_REWARD_FIELD_NUMBER: _ClassVar[int]
    STEPS_TAKEN_FIELD_NUMBER: _ClassVar[int]
    TOOL_CALLS_FIELD_NUMBER: _ClassVar[int]
    QUALITY_SCORE_FIELD_NUMBER: _ClassVar[int]
    EFFICIENCY_SCORE_FIELD_NUMBER: _ClassVar[int]
    WALL_TIME_SECONDS_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    completion_reason: CompletionReason
    total_reward: float
    steps_taken: int
    tool_calls: int
    quality_score: float
    efficiency_score: float
    wall_time_seconds: float
    def __init__(self, task_id: _Optional[str] = ..., completion_reason: _Optional[_Union[CompletionReason, str]] = ..., total_reward: _Optional[float] = ..., steps_taken: _Optional[int] = ..., tool_calls: _Optional[int] = ..., quality_score: _Optional[float] = ..., efficiency_score: _Optional[float] = ..., wall_time_seconds: _Optional[float] = ...) -> None: ...

class AbortTaskRequest(_message.Message):
    __slots__ = ("run_id", "task_id", "idempotency_key", "error_message")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    task_id: str
    idempotency_key: str
    error_message: str
    def __init__(self, run_id: _Optional[str] = ..., task_id: _Optional[str] = ..., idempotency_key: _Optional[str] = ..., error_message: _Optional[str] = ...) -> None: ...

class AbortTaskResponse(_message.Message):
    __slots__ = ("run_id", "task_result")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    TASK_RESULT_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    task_result: TaskResult
    def __init__(self, run_id: _Optional[str] = ..., task_result: _Optional[_Union[TaskResult, _Mapping]] = ...) -> None: ...

class CloseRunRequest(_message.Message):
    __slots__ = ("run_id", "idempotency_key", "reason", "error_message")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    idempotency_key: str
    reason: CloseRunReason
    error_message: str
    def __init__(self, run_id: _Optional[str] = ..., idempotency_key: _Optional[str] = ..., reason: _Optional[_Union[CloseRunReason, str]] = ..., error_message: _Optional[str] = ...) -> None: ...

class CloseRunResponse(_message.Message):
    __slots__ = ("run_id", "state")
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    run_id: str
    state: RunState
    def __init__(self, run_id: _Optional[str] = ..., state: _Optional[_Union[RunState, str]] = ...) -> None: ...
