import asyncio
from types import TracebackType
from typing import Any
from uuid import uuid4

from loguru import logger

from ..base import BaseTaskClient
from .errors import (
    RemoteClientStateError,
    RemoteProtocolError,
    RemoteRequestError,
)
from .models import (
    CloseRunCommand,
    CloseRunReason,
    CreateRunCommand,
    DeadlinePolicy,
    DynamicValueLimits,
    LeasedTask,
    LeaseTaskCommand,
    QueueExhausted,
    RemoteRun,
    RetryPolicy,
    _validate_dynamic_object,
)
from .session import RemoteBenchmarkSession
from .transport.base import RemoteTransport
from .transport.grpc import GrpcRemoteTransport


class RemoteBenchmarkClient(BaseTaskClient):
    """Transport-independent client for server-hosted investigation tasks."""

    def __init__(
        self,
        *,
        endpoint: str | None = None,
        token: str | None = None,
        run_label: str | None = None,
        agent_name: str | None = None,
        model_name: str | None = None,
        arena: str | None = None,
        metadata: dict[str, Any] | None = None,
        verify_tls: bool = True,
        deadlines: DeadlinePolicy | None = None,
        retry_policy: RetryPolicy | None = None,
        transport: RemoteTransport | None = None,
    ) -> None:
        """
        Configure a client that creates and owns one new remote run.

        Args:
            endpoint: gRPC target required when a transport is not injected.
            token: Bearer credential required when a transport is not injected.
            run_label: Optional diagnostic run label.
            agent_name: Optional diagnostic agent name.
            model_name: Optional diagnostic model name.
            arena: Competition stage to run in; the open one is used when omitted.
            metadata: Optional bounded canonical diagnostic metadata.
            verify_tls: Whether an SDK-owned gRPC channel verifies TLS.
            deadlines: Optional per-operation deadlines for the SDK-owned transport.
            retry_policy: Optional retry behavior for the SDK-owned transport.
            transport: Caller-owned transport for advanced configuration or tests.

        Raises:
            ValueError: If construction inputs or ownership are inconsistent.

        """
        self._transport: RemoteTransport
        self._owned_transport: RemoteTransport | None
        if transport is None:
            if endpoint is None or token is None:
                raise ValueError("endpoint and token are required without an injected transport")
            self._owned_transport = GrpcRemoteTransport(
                endpoint=endpoint,
                token=token,
                verify_tls=verify_tls,
                deadlines=deadlines,
                retry_policy=retry_policy,
            )
            self._transport = self._owned_transport
        else:
            if endpoint is not None or token is not None:
                raise ValueError("endpoint and token cannot be combined with an injected transport")
            if deadlines is not None or retry_policy is not None:
                raise ValueError(
                    "deadlines and retry_policy cannot be combined with an injected transport"
                )
            self._transport = transport
            self._owned_transport = None
        self._value_limits = DynamicValueLimits()
        self._run_label = run_label
        self._agent_name = agent_name
        self._model_name = model_name
        self._arena = arena
        self._metadata = dict(metadata or {})
        self._state = "new"
        self._run: RemoteRun | None = None
        self._lock = asyncio.Lock()

    def __repr__(self) -> str:
        """
        Return a representation without endpoint credentials or metadata.

        Returns:
            Sanitized client representation.

        """
        return f"RemoteBenchmarkClient(state={self._state!r})"

    @property
    def run(self) -> RemoteRun | None:
        """
        Return created run metadata when the client is open.

        Returns:
            Current run metadata or `None` before opening.

        """
        return self._run

    async def open(self) -> RemoteRun:
        """
        Create one new remote run.

        Returns:
            Created run metadata, or the existing metadata when already open.

        Raises:
            RemoteClientStateError: If the client was already closed.
            RemoteRequestError: If run metadata is not canonical.
            RemoteProtocolError: If the runtime does not create an active run.

        """
        async with self._lock:
            if self._state == "open" and self._run is not None:
                return self._run
            if self._state == "closed":
                raise RemoteClientStateError("A closed remote client cannot be reopened.")
            try:
                _validate_dynamic_object(self._metadata, limits=self._value_limits)
                command = CreateRunCommand(
                    idempotency_key=self._new_id(),
                    label=self._run_label,
                    agent_name=self._agent_name,
                    model_name=self._model_name,
                    metadata=self._metadata,
                    arena=self._arena,
                )
            except ValueError:
                raise RemoteRequestError(
                    "The remote run configuration contains invalid input."
                ) from None
            try:
                run = await self._transport.create_run(command)
                if run.state != "active":
                    raise RemoteProtocolError("The runtime did not create an active run.")
            except BaseException:
                self._state = "closed"
                if self._owned_transport is not None:
                    await self._owned_transport.aclose()
                raise
            self._run = run
            self._state = "open"
            return run

    async def start_task(self) -> RemoteBenchmarkSession | None:
        """
        Lease the next task from the open remote run.

        Returns:
            Remote session, or `None` only on explicit queue exhaustion.

        Raises:
            RemoteClientStateError: If the client is not open.
            RemoteProtocolError: If a custom transport returns mismatched run state.

        """
        async with self._lock:
            run = self._require_open_run()
            outcome = await self._transport.lease_task(
                LeaseTaskCommand(
                    run_id=run.run_id,
                    idempotency_key=self._new_id(),
                )
            )
            if outcome.run_id != run.run_id:
                raise RemoteProtocolError("The transport returned a mismatched run identifier.")
            if isinstance(outcome, QueueExhausted):
                return None
            if not isinstance(outcome, LeasedTask):
                raise RemoteProtocolError("The transport returned an unsupported lease outcome.")
            return RemoteBenchmarkSession(
                run_id=run.run_id,
                task=outcome.task,
                transport=self._transport,
                is_client_open=self._is_open,
                value_limits=self._value_limits,
            )

    async def aclose(
        self,
        *,
        reason: CloseRunReason = "client_requested",
        error_message: str | None = None,
    ) -> None:
        """
        Close the remote run and then any owned transport resources.

        Args:
            reason: Caller-visible reason for closing an incomplete run.
            error_message: Safe diagnostic captured by the client.

        Raises:
            Exception: The original run-close or transport-close failure after cleanup.

        """
        async with self._lock:
            if self._state == "closed":
                return
            run = self._run
            self._state = "closed"
            close_error: BaseException | None = None
            if run is not None:
                try:
                    await self._transport.close_run(
                        CloseRunCommand(
                            run_id=run.run_id,
                            idempotency_key=self._new_id(),
                            reason=reason,
                            error_message=error_message,
                        )
                    )
                except BaseException as exc:
                    close_error = exc
            if self._owned_transport is not None:
                try:
                    await self._owned_transport.aclose()
                except BaseException as exc:
                    if close_error is None:
                        close_error = exc
            if close_error is not None:
                raise close_error

    async def __aenter__(self) -> "RemoteBenchmarkClient":
        """
        Open a new remote run and return this client.

        Returns:
            Open remote client.

        """
        await self.open()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """
        Close the run and owned resources on context exit.

        Args:
            exc_type: Exception type raised inside the context.
            exc_value: Exception value raised inside the context.
            traceback: Exception traceback raised inside the context.

        """
        reason: CloseRunReason = "client_requested"
        error_message: str | None = None
        if exc_value is not None:
            if isinstance(exc_value, (asyncio.CancelledError, KeyboardInterrupt, SystemExit)):
                reason = "client_interrupted"
            else:
                reason = "client_error"
            error_message = f"{type(exc_value).__name__}: {exc_value}"
        try:
            await self.aclose(reason=reason, error_message=error_message)
        except BaseException as close_error:
            if exc_value is None:
                raise
            logger.opt(exception=close_error).warning(
                "Remote client cleanup failed while preserving the context exception"
            )

    def _require_open_run(self) -> RemoteRun:
        """
        Return the active run or reject the current client state.

        Returns:
            Active remote run metadata.

        Raises:
            RemoteClientStateError: If the client is not open.

        """
        if not self._is_open() or self._run is None:
            raise RemoteClientStateError("The remote client must be open before leasing tasks.")
        return self._run

    def _is_open(self) -> bool:
        """
        Return whether sessions may start new operations.

        Returns:
            Whether the parent client remains open.

        """
        return self._state == "open"

    def _new_id(self) -> str:
        """
        Generate one logical request identifier via UUIDv4.

        Returns:
            Non-empty logical identifier.

        """
        return uuid4().hex
