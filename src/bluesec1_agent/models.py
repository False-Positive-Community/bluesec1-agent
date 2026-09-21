from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Base model that rejects fields outside the public structured contract."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class SearchRequest(StrictModel):
    """Find entities and relations whose id or attributes contain a substring."""

    tool: Literal["search"]
    query: str = Field(min_length=5)


class GetEntityRequest(StrictModel):
    """Read one entity and the ids of its incoming and outgoing relations."""

    tool: Literal["get_entity"]
    entity_id: str = Field(min_length=1)


class GetRelationRequest(StrictModel):
    """Read one relation, including the entities it connects."""

    tool: Literal["get_relation"]
    relation_id: str = Field(min_length=1)


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


class FinishInvestigationRequest(StrictModel):
    """Submit the final BlueSec1 verdict and discovered response artifacts."""

    tool: Literal["finish_investigation"]
    verdict: Literal["benign", "malicious"]
    ir_artifacts: list[FinishInvestigationArtifact]
    reasoning: str = Field(min_length=1)


InvestigationFunction = (
    SearchRequest | GetEntityRequest | GetRelationRequest | FinishInvestigationRequest
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
