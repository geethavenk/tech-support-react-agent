# Technical Support ReAct Agent

A small technical-support agent built with LangGraph. It reads a customer's problem, picks diagnostic tools one step at a time (Reason → Act → Observe), and ends with a structured troubleshooting answer.

The tools are simulated: they return fixed sample output, so you can try the agent without real infrastructure.

## Project structure

| File | What it does |
|---|---|
| `agent.py` | LLM setup, system prompt, and the LangGraph graph (agent node, tool node, routing) |
| `tools.py` | Simulated diagnostic tools |
| `main.py` | Entry point: example scenarios, an interactive mode, and a printer for the agent's steps |

## Tools

| Tool | Purpose |
|---|---|
| `check_app_status` | Overall app health: CPU, memory, uptime, active requests |
| `check_server_logs` | Recent logs for a service (`"orders"` or `"auth"`) |
| `check_db_status` | Database connection pool and latency |
| `check_api_health` | API status code and response time |
| `search_internal_docs` | Runbooks for common problems |

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in your keys
```

`.env` settings:

| Variable | Description |
|---|---|
| `API_KEY` | API key for the OpenAI-compatible model endpoint |
| `BASE_URL` | Base URL of that endpoint |
| `LANGSMITH_TRACING` | `true` to send traces to LangSmith (optional) |
| `LANGSMITH_API_KEY` | LangSmith API key (optional) |
| `LANGSMITH_PROJECT` | LangSmith project name (optional) |

## Usage

Run the scenario set at the bottom of `main.py`:

```bash
python main.py
```

Chat with the agent:

```bash
python main.py --interactive
```

Type `exit` to quit.

Available scenarios (`SCENARIOS` in `main.py`): `api_500`, `slow`, `login`, `database`, `docker`. To run a different one, change the `run_scenario("...")` call at the bottom of `main.py`.

## Example output

Each tool call is printed with the model's reason for choosing it:

```
[AIMessage]
Tool selected: check_server_logs
Reason: The user is unable to log in, indicating a possible authentication or login service error...
Arguments: {'service': 'auth'}
```

The final answer always covers: Problem, Investigation performed, Likely root cause, Recommended action, and whether escalation is required.

## How it works

- **Agent loop:** `agent` node → (tool calls?) → `tools` node → back to `agent`, until the model answers without calling a tool.
- **Iteration limit:** `MAX_ITERATIONS` in `agent.py` caps the number of model calls. When the cap is reached, the agent must answer using the evidence it has already collected.
- **Reason for each tool call:** `agent.py` adds a required `reason` argument to every tool's schema before sending it to the model, and removes it again before the tool runs. The tool functions in `tools.py` stay unchanged.
- **Error handling:** model and tool errors are caught and turned into messages, so a failure doesn't crash the run.
