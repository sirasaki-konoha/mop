# Codex guidance for MOP

This repository provides MOP, a shared Streamable HTTP MCP server for recording
and coordinating multi-agent work. The server is available to Codex in this
project as `mop` when `.venv` has been prepared and `src/http_entry.py` is
running at `http://127.0.0.1:8765/mcp`.

## When to use MOP

Use MOP when the user explicitly requests multi-agent orchestration, task
tracking, agent-to-agent communication, artifact review, or result merging.
Do not use it for ordinary small edits, questions, or single-agent tasks solely
to create process records.

MOP records workflow state; `assign_agent` does not start an agent. Live
messages are shared only when every participant connects to the same HTTP
server process. A delivered message does not start or wake an idle model by
itself; the receiving client must call `get_agent_inbox` or have an active
`wait_for_agent_message` call. Only assign work that has a real execution plan,
and perform the work with Codex's available collaboration mechanisms as
appropriate.

## MOP workflow

1. Call `list_registered_agents`. Register Codex with `register_agent` only if
   no suitable Codex agent is already registered. Use a stable ID such as
   `codex` and describe the actual role for this task.
2. Call `decompose_task` once for the user request. Keep the resulting task ID
   and use its subtask IDs; do not create duplicate root tasks for retries.
3. Before parallel work begins, use `assign_agent` to record the intended
   owner of each actionable subtask. Keep assignments aligned with actual
   agents or roles.
4. Use `agent_communicate` for decisions, blockers, handoffs, or review
   requests that need to remain in the task record. Include the relevant
   `task_id`.
5. After completing a meaningful deliverable, call `submit_artifact` with its
   real repository path, an accurate content summary, and the appropriate
   artifact type. Never submit placeholder artifacts.
6. Use `get_task_status` before reporting progress or starting final
   integration. Review submitted code with `review_code` when a review is in
   scope; address rejected work before merging.
7. Call `merge_results` only after the needed subtasks and artifacts are ready.
   Report the merge result and any remaining blockers truthfully.

## Live messaging

1. Call `get_agent_inbox` before waiting. Keep the returned
   `latest_message_id` as the inbox cursor.
2. Call `wait_for_agent_message` with the receiving `agent_id`, that cursor as
   `after_message_id`, and a timeout of at most 30 seconds under the default
   Codex tool timeout.
3. After a message arrives, process it and reply with `agent_communicate`.
   Continue waiting only when the user asked for monitoring or an active
   multi-agent workflow requires it.
4. Do not launch `src/mcp_entry.py` for cross-client communication. That stdio
   mode creates isolated state for each client. Use `src/http_entry.py` once
   and point every client at the same URL.

## Safety and verification

- Treat MOP tool output as workflow metadata, not proof that implementation or
  tests succeeded. Run the repository's relevant verification commands before
  claiming completion.
- MOP state is currently process-local and is lost when the shared HTTP server
  restarts. Do not treat it as durable storage.
- Preserve task IDs and artifact IDs in handoffs and summaries where they help
  the user inspect work.
- Do not expose secrets, credentials, or unrelated local file contents through
  artifact submissions or agent messages.
