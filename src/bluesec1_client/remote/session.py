import asyncio
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from ..base import BaseTaskSession
from ..errors import TaskAlreadyFinishedError
from ..protocols import PublicTask, TaskResult, ToolCallResult
from .errors import (
    RemoteClientStateError,
    RemoteProtocolError,
    RemoteRequestError,
)
from .models import (
    AbortTaskCommand,
    CallToolCommand,
    DynamicValueLimits,
    _validate_dynamic_object,
)
from .transport.base import RemoteTransport


class RemoteBenchmarkSession(BaseTaskSession):
    """Transport-independent session for one leased remote task."""

    def __init__(
        self,
        *,
        run_id: str,
        task: PublicTask,
        transport: RemoteTransport,
        is_client_open: Callable[[], bool],
        value_limits: DynamicValueLimits,
    ) -> None:
        """
        Bind one public task to its remote transport context.

        Args:
            run_id: Owning remote run identifier.
            task: Leased public task payload.
            transport: Transport used for task operations.
            is_client_open: Callback exposing parent-client availability.
            value_limits: Canonical tool-argument bounds.

        """
        self._run_id = run_id
        self._task = task
        self._transport = transport
        self._is_client_open = is_client_open
        self._value_limits = value_limits
        self._terminal_result: TaskResult | None = None
        self._aborted_result: TaskResult | None = None
        self._lock = asyncio.Lock()

    @property
    def task(self) -> PublicTask:
        """
        Return the public task payload for this session.

        Returns:
            Leased public task.

        """
        return self._task

    @property
    def run_id(self) -> str:
        """
        Return the owning remote run identifier.

        Returns:
            Remote run identifier.

        """
        return self._run_id

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolCallResult:
        """
        Invoke one tool and update local terminal state.

        Args:
            tool_name: Non-empty public runtime tool name.
            arguments: Canonical recursive tool arguments.

        Returns:
            Public tool-call result.

        Raises:
            RemoteClientStateError: If the parent client has closed.
            TaskAlreadyFinishedError: If this session is already terminal.
            RemoteRequestError: If local tool inputs are invalid.
            RemoteProtocolError: If a fake or custom transport returns mismatched identifiers.

        """
        async with self._lock:
            self._require_active()
            if not isinstance(arguments, dict):
                raise RemoteRequestError("Tool arguments must be a string-keyed object.")
            try:
                _validate_dynamic_object(arguments, limits=self._value_limits)
                command = CallToolCommand(
                    run_id=self._run_id,
                    task_id=self.task_id,
                    call_id=self._new_id(),
                    tool_name=tool_name,
                    arguments=arguments,
                )
            except ValueError:
                raise RemoteRequestError("The tool call contains invalid input.") from None
            outcome = await self._transport.call_tool(command)
            result = outcome.result
            if (
                outcome.run_id != self._run_id
                or outcome.call_id != command.call_id
                or result.task_id != self.task_id
                or result.tool_name != tool_name
            ):
                raise RemoteProtocolError(
                    "The transport returned mismatched tool-call identifiers."
                )
            if result.task_result is not None:
                if (
                    type(result.task_result) is not TaskResult
                    or result.task_result.task_id != self.task_id
                ):
                    raise RemoteProtocolError(
                        "The transport returned an invalid public task result."
                    )
                if not (result.terminated or result.truncated):
                    raise RemoteProtocolError("The transport returned invalid terminal task state.")
                self._terminal_result = result.task_result
            elif result.terminated or result.truncated:
                raise RemoteProtocolError("The transport omitted the terminal task result.")
            return result

    async def abort_task(self, *, error_message: str | None = None) -> TaskResult:
        """
        Abort this task and cache the successful terminal result.

        Args:
            error_message: Optional bounded public failure description.

        Returns:
            Original cached abort result on every successful repetition.

        Raises:
            RemoteClientStateError: If the parent client has closed.
            TaskAlreadyFinishedError: If the task completed normally.
            RemoteRequestError: If the error message is invalid.
            RemoteProtocolError: If a custom transport returns mismatched identifiers.

        """
        async with self._lock:
            if not self._is_client_open():
                raise RemoteClientStateError("The parent remote client is closed.")
            if self._aborted_result is not None:
                return self._aborted_result
            if self._terminal_result is not None:
                raise TaskAlreadyFinishedError("The remote task has already finished.")
            try:
                command = AbortTaskCommand(
                    run_id=self._run_id,
                    task_id=self.task_id,
                    idempotency_key=self._new_id(),
                    error_message=error_message,
                )
            except ValueError:
                raise RemoteRequestError("The task-abort request contains invalid input.") from None
            outcome = await self._transport.abort_task(command)
            if (
                outcome.run_id != self._run_id
                or type(outcome.task_result) is not TaskResult
                or outcome.task_result.task_id != self.task_id
            ):
                raise RemoteProtocolError("The transport returned mismatched abort identifiers.")
            self._terminal_result = outcome.task_result
            self._aborted_result = outcome.task_result
            return outcome.task_result

    def _require_active(self) -> None:
        """
        Require an open parent client and non-terminal task.

        Raises:
            RemoteClientStateError: If the parent client has closed.
            TaskAlreadyFinishedError: If this task is already terminal.

        """
        if not self._is_client_open():
            raise RemoteClientStateError("The parent remote client is closed.")
        if self._terminal_result is not None:
            raise TaskAlreadyFinishedError("The remote task has already finished.")

    def _new_id(self) -> str:
        """
        Generate and validate one logical request identifier.

        Returns:
            Non-empty logical identifier.

        Raises:
            RemoteClientStateError: If the configured factory returns an invalid value.

        """
        logical_id = uuid4().hex
        if not logical_id or len(logical_id) > 255:
            raise RemoteClientStateError("The remote request-id factory returned an invalid value.")
        return logical_id
