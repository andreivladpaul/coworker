# Coworker - README

This document describes the structure of the **Coworker** project and the role of its three main files:

- `coworker.py`
- `coworker_tools.py`
- `app.py`

The goal is to build an AI coworker agent that can:

- receive a task with success criteria,
- use real tools (browser, filesystem, web search, notifications),
- pause when human approval is required,
- resume exactly from the point where it stopped.

---

## Architecture Overview

The architecture is split into three layers:

1. **Agent orchestration** (`coworker.py`)
2. **Tool integration and MCP sessions** (`coworker_tools.py`)
3. **Gradio user interface** (`app.py`)

This separation keeps the project extensible and reusable across use cases.

---

## 1) `coworker.py` - Core Logic and Control Loop

`coworker.py` contains the `Coworker` class, which coordinates the full execution lifecycle.

### Main Responsibilities

- initialize worker, middleware, memory, and evaluator (`setup`),
- start a user turn (`run_turn`),
- handle pause/resume flow (`_advance`, `resume`),
- verify whether success criteria are met (`evaluate`),
- close external resources (`cleanup`).

### Key Components

- **`TolerateToolErrors`**: custom middleware that catches tool errors and returns them as `ToolMessage` instead of crashing the run.
- **`HumanInTheLoopMiddleware`**: pauses the run on sensitive tools (for example `send_push_notification`, `request_human_help`).
- **`TodoListMiddleware`**: maintains a live todo list shown in the UI.
- **`PIIMiddleware`**: redacts PII in tool input/output.
- **`ModelCallLimitMiddleware`**: prevents infinite loops by limiting model calls.

### Turn Execution Flow

1. `run_turn()` saves task and criteria, builds the payload, and calls `_advance()`.
2. `_advance()` streams worker execution.
3. If `__interrupt__` appears, it sets state to `paused` and returns to the UI.
4. If there is no interrupt, it takes the response and sends it to `evaluate()`.
5. If criteria are not satisfied, it generates feedback and retries (up to `MAX_ATTEMPTS`).
6. `resume()` creates `Command(resume=...)` and continues on the same thread.

---

## 2) `coworker_tools.py` - Tooling and Persistent Sessions

`coworker_tools.py` defines tools and manages MCP sessions (browser + filesystem).

### Included Tools

- `search` (Serper)
- `wikipedia_lookup`
- `send_push_notification`
- `request_human_help`
- MCP tools dynamically loaded from:
  - Playwright server (browser)
  - Filesystem server (sandbox)

### `McpSessions`: Why It Matters

The `McpSessions` class keeps persistent MCP sessions open across tool calls.

- `_run()` opens sessions and loads tools.
- `self._ready.set()` signals that servers are ready.
- `_stop.wait()` keeps the task alive until stop is requested.
- `stop()` triggers graceful shutdown.

This approach is essential to preserve browser state during long-running tasks.

### Filesystem Sandbox

The filesystem MCP server starts with a dedicated `sandbox` root, so files produced by the agent stay confined to a controlled directory.

---

## 3) `app.py` - UI and Event Wiring

`app.py` exposes Coworker through Gradio.

### Main Functions

- `setup()`: creates a `Coworker` instance and starts tools/sessions.
- `process_message()`: sends a user request to `run_turn()`.
- `approve()`: calls `resume()` when the run is paused.
- `watch_todos()`: periodically refreshes the plan/todo panel.
- `reset()`: closes sessions and recreates Coworker from scratch.

### Approval Button Visibility

The "Approve and continue" button is controlled by `coworker.paused`:

- visible only when an interrupt is active,
- hidden when execution resumes or completes.

---

## End-to-End Flow

1. The UI starts with `setup()`.
2. `coworker.setup()` loads tools, worker, middleware, and evaluator.
3. The user sends a task and success criteria.
4. The worker runs with real tools.
5. If approval is needed, execution pauses and the UI shows the button.
6. With `approve()`, execution resumes from the exact stop point.
7. The evaluator decides whether the task is complete or needs another attempt.
8. `cleanup()` closes MCP servers and the browser.

---

## How To Extend The Project

- Add custom tools in `coworker_tools.py`.
- Extend `interrupt_on` to require approval for additional actions.
- Customize `WORKER_PROMPT` for new domains.
- Strengthen the evaluator with more specific rubrics.
- Evolve the UI with `approve/reject/edit` options per action request.

---

## Operational Notes

- The project uses environment variables (`.env`) for API keys and notifications.
- Browser and filesystem MCP servers run in persistent sessions, so proper reset/cleanup is important.
- On Windows/Jupyter setups, you may need the stderr patch documented in the lab notebook.

---

