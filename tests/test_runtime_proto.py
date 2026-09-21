from google.protobuf import descriptor_pb2

from bluesec1_client.proto.investigation.runtime.v1 import runtime_pb2, runtime_pb2_grpc


def test_generated_service_exposes_the_complete_v1_runtime() -> None:
    """Keep the public service surface synchronized with scenario-runtime."""
    service = runtime_pb2.DESCRIPTOR.services_by_name["ScenarioRuntime"]

    assert [method.name for method in service.methods] == [
        "CreateRun",
        "LeaseTask",
        "CallTool",
        "AbortTask",
        "CloseRun",
    ]
    assert runtime_pb2_grpc.ScenarioRuntimeStub is not None


def test_create_and_close_run_publish_the_competition_contract() -> None:
    """Expose arena selection plus structured client close diagnostics."""
    create_fields = {
        field.name: field.number for field in runtime_pb2.CreateRunRequest.DESCRIPTOR.fields
    }
    close_fields = {
        field.name: field.number for field in runtime_pb2.CloseRunRequest.DESCRIPTOR.fields
    }

    assert create_fields == {
        "idempotency_key": 1,
        "label": 2,
        "agent_name": 3,
        "model_name": 4,
        "metadata": 5,
        "arena": 6,
    }
    assert close_fields == {
        "run_id": 1,
        "idempotency_key": 2,
        "reason": 3,
        "error_message": 4,
    }
    assert runtime_pb2.CloseRunReason.keys() == [
        "CLOSE_RUN_REASON_UNSPECIFIED",
        "CLOSE_RUN_REASON_CLIENT_REQUESTED",
        "CLOSE_RUN_REASON_CLIENT_ERROR",
        "CLOSE_RUN_REASON_CLIENT_INTERRUPTED",
    ]


def test_runtime_errors_publish_competition_start_refusals() -> None:
    """Keep stable arena and run-start rate-limit reasons in the public enum."""
    reasons = runtime_pb2.RuntimeErrorReason.keys()

    assert runtime_pb2.COMPETITION_ARENA_CLOSED == 25
    assert runtime_pb2.SUBJECT_RUN_START_RATE_LIMIT_REACHED == 26
    assert "COMPETITION_ARENA_CLOSED" in reasons
    assert "SUBJECT_RUN_START_RATE_LIMIT_REACHED" in reasons


def test_task_result_is_contiguous_and_has_no_legacy_reservations() -> None:
    """Publish only final public scores in a fresh contiguous field layout."""
    descriptor = runtime_pb2.TaskResult.DESCRIPTOR
    assert {field.name: field.number for field in descriptor.fields} == {
        "task_id": 1,
        "completion_reason": 2,
        "total_reward": 3,
        "steps_taken": 4,
        "tool_calls": 5,
        "quality_score": 6,
        "efficiency_score": 7,
        "wall_time_seconds": 8,
    }

    file_descriptor = descriptor_pb2.FileDescriptorProto.FromString(
        runtime_pb2.DESCRIPTOR.serialized_pb
    )
    task_result = next(
        message for message in file_descriptor.message_type if message.name == "TaskResult"
    )
    assert list(task_result.reserved_range) == []
    assert list(task_result.reserved_name) == []
