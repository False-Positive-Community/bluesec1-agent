from abc import ABC, abstractmethod

from ..models import (
    AbortTaskCommand,
    AbortTaskOutcome,
    CallToolCommand,
    CloseRunCommand,
    CloseRunOutcome,
    CreateRunCommand,
    LeaseTaskCommand,
    LeaseTaskOutcome,
    RemoteRun,
    ToolCallOutcome,
)


class RemoteTransport(ABC):
    """Transport-neutral asynchronous runtime interface."""

    @abstractmethod
    async def create_run(self, command: CreateRunCommand) -> RemoteRun:
        """
        Create a new remote run.

        Args:
            command: Idempotent run-creation command.

        Returns:
            Created run metadata.

        """
        raise NotImplementedError

    @abstractmethod
    async def lease_task(self, command: LeaseTaskCommand) -> LeaseTaskOutcome:
        """
        Lease a task or report explicit queue exhaustion.

        Args:
            command: Idempotent task-lease command.

        Returns:
            Leased task or queue-exhaustion outcome.

        """
        raise NotImplementedError

    @abstractmethod
    async def call_tool(self, command: CallToolCommand) -> ToolCallOutcome:
        """
        Invoke a tool for an active task.

        Args:
            command: Correlated tool-call command.

        Returns:
            Correlated public tool result.

        """
        raise NotImplementedError

    @abstractmethod
    async def abort_task(self, command: AbortTaskCommand) -> AbortTaskOutcome:
        """
        Abort an active task.

        Args:
            command: Idempotent abort command.

        Returns:
            Final public task result.

        """
        raise NotImplementedError

    @abstractmethod
    async def close_run(self, command: CloseRunCommand) -> CloseRunOutcome:
        """
        Close a run and its active server-side tasks.

        Args:
            command: Idempotent close command.

        Returns:
            Closed or closing run state.

        """
        raise NotImplementedError

    @abstractmethod
    async def aclose(self) -> None:
        """Close resources owned by this transport."""
        raise NotImplementedError
