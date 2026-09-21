import asyncio

import grpc
import pytest
from google.protobuf import any_pb2
from google.rpc import error_details_pb2, status_pb2
from grpc.aio import Metadata
from pydantic import ValidationError

from bluesec1_client import RemoteBenchmarkClient, TaskResult
from bluesec1_client.proto.investigation.runtime.v1 import runtime_pb2
from bluesec1_client.remote.errors import CompetitionClosedError, RemoteRateLimitError
from bluesec1_client.remote.models import (
    CloseRunCommand,
    CreateRunCommand,
    DynamicValueLimits,
    RemoteRun,
    RetryPolicy,
)
from bluesec1_client.remote.transport.grpc import map_grpc_error
from bluesec1_client.remote.transport.mappers import (
    DynamicValueCodec,
    decode_task_result,
    encode_close_run,
    encode_create_run,
)


class FakeTransport:
    """Record lifecycle commands without opening a network connection."""

    def __init__(self) -> None:
        """Initialize command capture lists."""
        self.create_commands: list[CreateRunCommand] = []
        self.close_commands: list[CloseRunCommand] = []

    async def create_run(self, command: CreateRunCommand) -> RemoteRun:
        """Record run creation and return an active run."""
        self.create_commands.append(command)
        return RemoteRun(run_id="run-1", state="active")

    async def close_run(self, command: CloseRunCommand) -> None:
        """Record run closure."""
        self.close_commands.append(command)


def make_rpc_error(code: grpc.StatusCode, *, reason: str) -> grpc.aio.AioRpcError:
    """Build a gRPC failure carrying one stable runtime error reason."""
    packed_reason = any_pb2.Any()
    packed_reason.Pack(error_details_pb2.ErrorInfo(reason=reason, domain="runtime"))
    rich_status = status_pb2.Status(
        code=code.value[0],
        message="server detail",
        details=[packed_reason],
    )
    trailing = Metadata(("grpc-status-details-bin", rich_status.SerializeToString()))
    return grpc.aio.AioRpcError(
        code,
        trailing_metadata=trailing,
        details="server detail",
        debug_error_string="server debug detail",
    )


def test_run_commands_encode_arena_and_close_diagnostics() -> None:
    """Map every new lifecycle field to its protobuf counterpart."""
    codec = DynamicValueCodec(DynamicValueLimits())
    create = encode_create_run(
        CreateRunCommand(idempotency_key="create-1", arena="practice"),
        codec,
    )
    close = encode_close_run(
        CloseRunCommand(
            run_id="run-1",
            idempotency_key="close-1",
            reason="client_error",
            error_message="agent failed",
        )
    )

    assert create.arena == "practice"
    assert close.reason == runtime_pb2.CLOSE_RUN_REASON_CLIENT_ERROR
    assert close.error_message == "agent failed"


def test_task_result_decoder_returns_only_public_scores() -> None:
    """Decode the clean v1 score contract without internal scoring inputs."""
    result = decode_task_result(
        runtime_pb2.TaskResult(
            task_id="task-1",
            completion_reason=runtime_pb2.COMPLETION_REASON_TERMINATED,
            total_reward=42.0,
            steps_taken=8,
            tool_calls=7,
            quality_score=0.9,
            efficiency_score=0.8,
            wall_time_seconds=12.5,
        )
    )

    assert isinstance(result, TaskResult)
    assert result.model_dump() == {
        "task_id": "task-1",
        "completion_reason": "terminated",
        "total_reward": 42.0,
        "steps_taken": 8,
        "tool_calls": 7,
        "quality_score": 0.9,
        "efficiency_score": 0.8,
        "wall_time_seconds": 12.5,
    }

    with pytest.raises(ValidationError):
        TaskResult(
            task_id="task-1",
            completion_reason="terminated",
            max_possible_reward=100.0,
        )


def test_client_propagates_arena_and_context_failure_on_close() -> None:
    """Send arena selection and structured failure details through client lifecycle."""
    transport = FakeTransport()

    async def exercise_client() -> None:
        client = RemoteBenchmarkClient(transport=transport, arena="graded")
        try:
            async with client:
                raise RuntimeError("boom")
        except RuntimeError:
            pass

    asyncio.run(exercise_client())

    assert transport.create_commands[0].arena == "graded"
    assert transport.close_commands[0].reason == "client_error"
    assert transport.close_commands[0].error_message == "RuntimeError: boom"


def test_competition_start_refusals_map_to_dedicated_client_errors() -> None:
    """Distinguish a closed arena from the participant run-start rate limit."""
    closed = map_grpc_error(
        make_rpc_error(
            grpc.StatusCode.FAILED_PRECONDITION,
            reason="COMPETITION_ARENA_CLOSED",
        ),
        retry_policy=RetryPolicy(),
        idempotent=True,
    )
    limited = map_grpc_error(
        make_rpc_error(
            grpc.StatusCode.RESOURCE_EXHAUSTED,
            reason="SUBJECT_RUN_START_RATE_LIMIT_REACHED",
        ),
        retry_policy=RetryPolicy(),
        idempotent=True,
    )

    assert isinstance(closed, CompetitionClosedError)
    assert isinstance(limited, RemoteRateLimitError)
    assert limited.reason == "SUBJECT_RUN_START_RATE_LIMIT_REACHED"
