from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Base Pydantic model that forbids undeclared fields."""

    model_config = ConfigDict(extra="forbid")


class PublicTask(StrictModel):
    """Minimal participant-facing task contract with only visible task state."""

    task_id: str
    observation: dict[str, Any] = Field(default_factory=dict)


class TaskResult(StrictModel):
    """Public result returned when an environment run completes or fails."""

    task_id: str
    completion_reason: Literal["terminated", "truncated", "error", "aborted"]
    total_reward: float = 0.0
    steps_taken: int = 0
    tool_calls: int = 0
    quality_score: float = 0.0
    efficiency_score: float = 0.0
    wall_time_seconds: float = 0.0


class ToolCallRequest(StrictModel):
    """One tool invocation request issued by an external agent."""

    task_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolCallResult(StrictModel):
    """Step response returned after routing one tool call into an active task."""

    task_id: str
    tool_name: str
    observation: dict[str, Any] = Field(default_factory=dict)
    reward: float = 0.0
    terminated: bool = False
    truncated: bool = False
    info: dict[str, Any] = Field(default_factory=dict)
    task_result: TaskResult | None = None
