from abc import ABC, abstractmethod
from typing import Any

from .protocols import PublicTask, TaskResult, ToolCallResult


class BaseTaskSession(ABC):
    """One live task session exposed through a transport-neutral client API."""

    @property
    @abstractmethod
    def task(self) -> PublicTask:
        """
        Return the task payload associated with this live session.

        Returns:
            Public task contract visible to the agent or SDK user.

        """
        raise NotImplementedError

    @property
    def task_id(self) -> str:
        """
        Return the public task id associated with this session.

        Returns:
            str: Task identifier stable across tool calls.

        """
        return self.task.task_id

    @abstractmethod
    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolCallResult:
        """
        Invoke one atomic server-side tool on behalf of the current task session.

        Args:
            tool_name (str): Public tool name understood by the task runtime.
            arguments (dict[str, Any]): Tool arguments encoded as a JSON-like mapping.

        Returns:
            ToolCallResult: Step result returned by the runtime after the tool call.

        """
        raise NotImplementedError

    @abstractmethod
    async def abort_task(self, *, error_message: str | None = None) -> TaskResult:
        """
        Force-finalize the live task after an external agent/runtime failure.

        Normal task execution does not need to call this method; tasks are
        finalized automatically when tool execution terminates or truncates the
        environment.
        """
        raise NotImplementedError


class BaseTaskClient(ABC):
    """Factory-like client that leases live task sessions from some task source."""

    @abstractmethod
    async def start_task(self) -> BaseTaskSession | None:
        """
        Lease the next available task session from the underlying runtime.

        Returns:
            BaseTaskSession | None: Live task session, or `None` when no tasks remain.

        """
        raise NotImplementedError
