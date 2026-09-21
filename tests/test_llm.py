import asyncio
from types import SimpleNamespace
from typing import Any, cast

import pytest
from openai import AsyncOpenAI

from bluesec1_agent.llm import (
    OpenAIStructuredStepClient,
    parse_next_step_payload,
)
from bluesec1_agent.models import (
    NEXT_STEP_RESPONSE_FORMAT,
    GetEntityRequest,
    NextStep,
)


class FakeCompletions:
    """Queue-backed fake for the OpenAI chat completion endpoint."""

    def __init__(self, contents: list[str]) -> None:
        """Store response content and request audit state."""
        self.contents = list(contents)
        self.requests: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        """Return the next queued assistant message."""
        self.requests.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=self.contents.pop(0),
                        refusal=None,
                    )
                )
            ],
            usage=SimpleNamespace(total_tokens=17),
        )


class FakeOpenAI:
    """Minimal object graph required by `OpenAIStructuredStepClient`."""

    def __init__(self, contents: list[str]) -> None:
        """Expose fake chat completions."""
        self.completions = FakeCompletions(contents)
        self.chat = SimpleNamespace(completions=self.completions)


def valid_process_step() -> NextStep:
    """Build one valid non-terminal graph navigation step."""
    return NextStep(
        current_state="The trigger entity needs its relations.",
        plan_remaining_steps_brief=["Read the trigger entity."],
        task_completed=False,
        function=GetEntityRequest(
            tool="get_entity",
            entity_id="entity-1",
        ),
    )


def test_structured_client_repairs_malformed_response() -> None:
    """Malformed provider output should be retried outside the main history."""
    fake_openai = FakeOpenAI(["not-json", valid_process_step().model_dump_json()])
    client = OpenAIStructuredStepClient(
        base_url="https://llm.example/v1",
        api_key="secret",
        model="test-model",
        timeout_seconds=10.0,
        max_completion_tokens=1000,
        max_retries=3,
        client=cast(AsyncOpenAI, fake_openai),
    )
    original_messages = [{"role": "system", "content": "Investigate."}]

    step = asyncio.run(client.next_step(original_messages))

    assert step.function.tool == "get_entity"
    assert len(fake_openai.completions.requests) == 2
    first_messages = fake_openai.completions.requests[0]["messages"]
    assert "Never use top-level `action`" in first_messages[0]["content"]
    assert "advertised_tool" in first_messages[0]["content"]
    repaired_messages = fake_openai.completions.requests[1]["messages"]
    assert repaired_messages[-1]["role"] == "user"
    assert original_messages == [{"role": "system", "content": "Investigate."}]


def test_parser_rejects_inconsistent_completion_flag() -> None:
    """A non-terminal function cannot claim that the investigation is complete."""
    payload = valid_process_step().model_copy(update={"task_completed": True}).model_dump_json()

    with pytest.raises(ValueError, match="task_completed"):
        parse_next_step_payload(payload)


def test_response_schema_requires_nullable_tool_fields() -> None:
    """Strict provider schema should require optional fields as nullable values."""
    schema = NEXT_STEP_RESPONSE_FORMAT["json_schema"]["schema"]
    process_schema = schema["$defs"]["GetEntityRequest"]

    assert set(process_schema["required"]) == set(process_schema["properties"])
    assert "default" not in str(schema)
    assert "discriminator" not in str(schema)
