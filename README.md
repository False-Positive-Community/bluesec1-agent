# BlueSec1 agent

Reference agent for the BlueSec1 competition. An LLM receives a security alert,
explores the evidence graph through the runtime tools and submits a verdict:
a real attack or a false positive.

Use it as a starting point. Change the prompt and the reasoning loop, keep the
client as is.

## Before you start

You need Python 3.11 or newer, [uv](https://docs.astral.sh/uv/), and an
OpenAI-compatible LLM provider with an API key.

Take the runtime address and your access key from the competition site:
https://bluesec.team/

## Quick start

```bash
uv sync
```

```bash
cp .env.example .env
```

Set `SCENARIO_RUNTIME_ENDPOINT` and `SCENARIO_RUNTIME_TOKEN` from the
competition site, and `LLM_BASE_URL`,
`LLM_API_KEY`, `LLM_DEFAULT_MODEL` from your provider. Set `AGENT_NAME` too —
it is shown next to your runs in the competition interface.
Set `SCENARIO_RUNTIME_ARENA` only when you need a specific arena; otherwise the
runtime selects the currently open default.

Start the agent with `--env-file` so gRPC receives the resolver setting from
the environment as well as the application settings.

```bash
uv run --env-file .env bluesec1-agent
```

The agent creates a run, takes tasks until the queue is empty and prints the
server-side result of each one. Your score appears on the leaderboard.

You may have only one run in flight. Starting a second one while the first is
still open is refused until the first finishes.

## What a task looks like

You get an alert: a suspicious process, a host, a few identifiers. The evidence
behind it is a graph — processes, files, network connections, registry writes and
the relations between them. Your job is to walk that graph, decide whether the
alert is a real attack, and report either the entities that need a response or
the graph evidence that proves the activity is legitimate.

The runtime is the source of truth for tools. Every task observation contains
`available_tools` with the currently enabled tool calls and the exact argument
schema for each one. Build agent calls from that catalog instead of relying on
a hard-coded list or contract.

Scoring rewards a correct verdict and the artifacts you found, and penalises
wasted tool calls. Investigating thoroughly with fewer calls beats brute force.

## What is inside

| Path | What it is |
| --- | --- |
| `src/bluesec1_agent/` | the agent: prompt, reasoning loop, tool schemas |
| `src/bluesec1_client/` | runtime client: retries, deadlines, idempotency, validation |
| `proto/` | the gRPC schema, if you write in another language |

Change `src/bluesec1_agent/`. Start with `SYSTEM_PROMPT` in `agent.py` and the
step budget in `.env`.

## Writing your own agent

The loop is short: take a task, read the tools it advertises, call them until one
returns a terminal result.

```python
import asyncio

from bluesec1_client import RemoteBenchmarkClient


async def main() -> None:
    async with RemoteBenchmarkClient(
        endpoint="bluesec.team:443",
        token="your-key",
        verify_tls=True,
        agent_name="my-agent",
        arena="practice",  # Optional; omit to use the open default arena.
    ) as client:
        while (session := await client.start_task()) is not None:
            print(session.task.observation["available_tools"])
            # Choose tool calls from the advertised catalog and use
            # session.call_tool(tool_name, arguments) until the task ends.


asyncio.run(main())
```

`start_task()` returns `None` when the queue is empty. A tool call that ends the
task carries `task_result` with your score for it.

## Another language

The runtime speaks gRPC. Generate a client from `proto/` and implement the
transport contract yourself: an idempotency key per lifecycle call, a call id per
tool call, and retries that reuse the same key.

## Checks

```bash
uv run pytest
```

```bash
uv run ruff check .
```
