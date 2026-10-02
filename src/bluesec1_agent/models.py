import re
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


class StrictModel(BaseModel):
    """Base model that rejects fields outside the public structured contract."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


ToolReasoning = Annotated[str, Field(min_length=1, max_length=4096)]
PropertyFieldName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

EntitySearchType = Literal[
    "host",
    "network_connection",
    "thread",
    "memory_region",
    "email",
    "email_url",
    "email_click",
    "email_attachment",
    "archive_file",
    "mounted_volume",
    "vpn_session",
    "app_object",
    "windows_process",
    "windows_file",
    "windows_user",
    "windows_service",
    "windows_driver",
    "registry_key",
    "named_pipe",
    "smb_share",
    "scheduled_task",
    "powershell_script",
    "powershell_cmdlet_invocation",
    "wmi_event_filter",
    "wmi_event_consumer",
    "wmi_binding",
    "com_object",
    "certificate_template",
    "x509_certificate",
    "kerberos_ticket",
    "lnk_shortcut",
    "ad_object",
    "linux_process",
    "linux_file",
    "linux_user",
    "linux_group",
    "systemd_unit",
    "kernel_module",
    "unix_socket",
    "ebpf_program",
]

RelationSearchType = Literal[
    "wrote_file",
    "read_file",
    "deleted_file",
    "renamed_file",
    "timestomped",
    "executed_file",
    "changed_file_mode",
    "changed_file_owner",
    "created_directory",
    "created_link",
    "truncated_file",
    "resolved_file_handle",
    "opened_by_handle",
    "created_memfd",
    "created_memfd_secret",
    "connected_to",
    "listened_on",
    "accepted_connection_from",
    "served_request_for",
    "sent_data_to",
    "received_data_from",
    "loaded_image",
    "allocated_memory",
    "mapped_memory",
    "created_thread",
    "created_service",
    "modified_service",
    "started_service",
    "stopped_service",
    "logged_on_to",
    "logged_off_from",
    "runs_process",
    "hosts",
    "mounted",
    "parent_of",
    "win_process_create",
    "injected_into",
    "accessed_process",
    "debugged_process",
    "elevated_token",
    "opened_handle",
    "duplicated_handle",
    "created_pipe",
    "connected_to_pipe",
    "opened_share_session",
    "created_scheduled_task",
    "ran_scheduled_task",
    "payload_references",
    "created_registry_key",
    "set_registry_value",
    "deleted_registry_key",
    "deleted_registry_value",
    "renamed_registry_key",
    "created_wmi_filter",
    "created_wmi_consumer",
    "bound_wmi_filter_to_consumer",
    "executed_script",
    "invoked_cmdlet",
    "loaded_driver",
    "created_shadow_copy",
    "received_email",
    "contained_url",
    "contained_attachment",
    "materialized_as",
    "performed_click",
    "targeted_url",
    "archived_to",
    "extracted_to",
    "contains_file",
    "mounted_as",
    "resolves_to",
    "created_account",
    "added_to_group",
    "removed_from_group",
    "requested_certificate",
    "issued_by_template",
    "authenticated_with_certificate",
    "requested_service_ticket",
    "dcsync_replication",
    "opened_handle_on_ad_object",
    "cleared_event_log",
    "remote_wmi_exec",
    "tunneled_via",
    "established_vpn_session",
    "tunneled_through",
    "forked",
    "execve_transitioned",
    "linux_process_create",
    "signal_sent",
    "ptrace_attached",
    "privilege_changed",
    "capabilities_changed",
    "controlled_tty",
    "changed_system_time",
    "changed_password",
    "changed_selinux_context",
    "changed_xattr",
    "created_unix_socket",
    "connected_to_unix_socket",
    "passed_fd",
    "loaded_kernel_module",
    "loaded_ebpf",
    "modified_audit_rules",
    "modified_audit_params",
    "created_group",
    "modified_group",
]


class EntitySearchScope(StrictModel):
    """Restrict search to one graph entity type."""

    kind: Literal["entity"]
    type: EntitySearchType


class RelationSearchScope(StrictModel):
    """Restrict search to one graph relation type."""

    kind: Literal["relation"]
    type: RelationSearchType


SearchScope = Annotated[EntitySearchScope | RelationSearchScope, Field(discriminator="kind")]


def _parse_time_boundary(value: object, *, upper: bool) -> datetime:
    """Parse a timezone-aware search boundary or an inclusive UTC calendar day."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("time_window boundaries must include a timezone")
        return value.astimezone(UTC)
    if not isinstance(value, str):
        raise ValueError("time_window boundaries must be ISO 8601 timestamp strings")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        day = datetime.fromisoformat(value).replace(tzinfo=UTC)
        return day.replace(hour=23, minute=59, second=59, microsecond=999999) if upper else day
    if not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})",
        value,
    ):
        raise ValueError("time_window boundaries must include a timezone or be calendar days")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


class SearchTimeWindow(StrictModel):
    """Inclusive timestamp range for graph search."""

    from_: datetime = Field(alias="from")
    to: datetime

    @field_validator("from_", mode="before")
    @classmethod
    def _parse_from(cls, value: object) -> datetime:
        """Parse the lower search boundary."""
        return _parse_time_boundary(value, upper=False)

    @field_validator("to", mode="before")
    @classmethod
    def _parse_to(cls, value: object) -> datetime:
        """Parse the upper search boundary."""
        return _parse_time_boundary(value, upper=True)

    @model_validator(mode="after")
    def _validate_bounds(self) -> "SearchTimeWindow":
        """Reject an inverted search window."""
        if self.from_ > self.to:
            raise ValueError("time_window.from must be before or equal to time_window.to")
        return self


class SearchRequest(StrictModel):
    """Find entities and relations whose id or attributes contain a substring."""

    tool: Literal["search"]
    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5)]
    reasoning: ToolReasoning
    page_id: int = Field(default=1, ge=1)
    scope: SearchScope | None = None
    time_window: SearchTimeWindow | None = None
    sort_order: Literal["ascending", "descending"] = "ascending"


class GetEntityRequest(StrictModel):
    """Read one entity and the ids of its incoming and outgoing relations."""

    tool: Literal["get_entity"]
    entity_id: str
    reasoning: ToolReasoning


class GetRelationRequest(StrictModel):
    """Read one relation, including the entities it connects."""

    tool: Literal["get_relation"]
    relation_id: str
    reasoning: ToolReasoning


class GetADObjectInfoRequest(StrictModel):
    """Read one Active Directory object and its navigation references."""

    tool: Literal["get_ad_object_info"]
    ad_object_id: str
    reasoning: ToolReasoning


IRArtifactKind = Literal[
    "host_to_isolate",
    "identity_to_rotate",
    "persistence_to_remove",
    "cleanup_to_verify",
    "file_to_delete",
    "network_block",
    "mailbox_action",
    "other",
    "process_observed",
    "registry_observed",
    "file_observed",
    "mount_observed",
    "lnk_observed",
    "ticket_observed",
    "identity_observed",
    "artifact_observed",
]


class FinishInvestigationArtifact(StrictModel):
    """One discovered entity and its requested incident-response action."""

    entity_id: str
    kind: IRArtifactKind


class FinishInvestigationEntityEvidence(StrictModel):
    """Cite observable entity properties supporting a benign verdict."""

    anchor: Literal["entity"]
    entity_id: str
    property_fields: list[PropertyFieldName] = Field(min_length=1)


class FinishInvestigationRelationEvidence(StrictModel):
    """Cite a relation or its properties supporting a benign verdict."""

    anchor: Literal["relation"]
    relation_id: str
    property_fields: list[PropertyFieldName] = Field(default_factory=list)


FinishInvestigationLegitimacyEvidence = Annotated[
    FinishInvestigationEntityEvidence | FinishInvestigationRelationEvidence,
    Field(discriminator="anchor"),
]


class MaliciousFinishInvestigationSubmission(StrictModel):
    """Submit a malicious verdict with incident-response artifacts."""

    verdict: Literal["malicious"]
    ir_artifacts: list[FinishInvestigationArtifact]
    reasoning: str


class BenignFinishInvestigationSubmission(StrictModel):
    """Submit a benign verdict with observable legitimacy evidence."""

    verdict: Literal["benign"]
    legitimacy_evidence: list[FinishInvestigationLegitimacyEvidence]
    reasoning: str


FinishInvestigationSubmission = Annotated[
    MaliciousFinishInvestigationSubmission | BenignFinishInvestigationSubmission,
    Field(discriminator="verdict"),
]


class FinishInvestigationRequest(StrictModel):
    """Submit the final BlueSec1 verdict and discovered response artifacts."""

    tool: Literal["finish_investigation"]
    submission: FinishInvestigationSubmission


InvestigationFunction = (
    SearchRequest
    | GetEntityRequest
    | GetRelationRequest
    | GetADObjectInfoRequest
    | FinishInvestigationRequest
)


class NextStep(StrictModel):
    """One validated reasoning-and-action turn produced by the LLM."""

    current_state: str
    plan_remaining_steps_brief: list[str] = Field(min_length=1, max_length=5)
    task_completed: bool
    function: InvestigationFunction = Field(description="Execute the first remaining step.")


def build_strict_json_schema() -> dict[str, Any]:
    """Build a provider-portable strict JSON Schema for `NextStep`.

    Returns:
        Schema with closed objects, required nullable fields, and no defaults.
    """
    schema = NextStep.model_json_schema(by_alias=True)
    _normalize_strict_schema(schema)
    return schema


def _normalize_strict_schema(node: Any) -> None:
    """Normalize nested schema nodes for strict OpenAI-compatible providers.

    Args:
        node: Mutable JSON Schema node or collection.
    """
    if isinstance(node, list):
        for record in node:
            _normalize_strict_schema(record)
        return
    if not isinstance(node, dict):
        return

    node.pop("default", None)
    node.pop("discriminator", None)
    if "oneOf" in node:
        node["anyOf"] = node.pop("oneOf")
    properties = node.get("properties")
    if node.get("type") == "object" and isinstance(properties, dict):
        node["additionalProperties"] = False
        node["required"] = list(properties)
    for value in node.values():
        _normalize_strict_schema(value)


NEXT_STEP_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "bluesec1_next_step",
        "strict": True,
        "schema": build_strict_json_schema(),
    },
}
