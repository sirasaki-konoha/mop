from __future__ import annotations

import dataclasses
import importlib
import json
import logging
import sys
import types
from pathlib import Path

# Bootstrap: bypass broken tools/__init__.py
_tools_path = str(Path(__file__).parent / "tools")
_tools_pkg = types.ModuleType("orchestrator.tools")
_tools_pkg.__path__ = [_tools_path]
_tools_pkg.__package__ = "orchestrator.tools"
sys.modules["orchestrator.tools"] = _tools_pkg

from orchestrator import Orchestrator
from orchestrator.storage.artifact_store import get_artifact_store
from orchestrator.storage.task_store import get_task_store

_decompose_mod = importlib.import_module("orchestrator.tools.decompose")
_assign_mod = importlib.import_module("orchestrator.tools.assign")
_merge_mod = importlib.import_module("orchestrator.tools.merge")
_review_mod = importlib.import_module("orchestrator.tools.review")
importlib.import_module("orchestrator.tools.communicate")
importlib.import_module("orchestrator.tools.status")
importlib.import_module("orchestrator.tools.artifact")

_tools_pkg.DecomposeTool = _decompose_mod.DecomposeTool
_tools_pkg.AssignTool = _assign_mod.AssignTool
_tools_pkg.MergeTool = _merge_mod.MergeTool
_tools_pkg.ReviewTool = _review_mod.ReviewTool
_tools_pkg.decompose_task = _decompose_mod.decompose_task
_tools_pkg.assign_agent = _assign_mod.assign_agent

from fastmcp import FastMCP

from orchestrator.tools.artifact import create_submit_artifact
from orchestrator.tools.communicate import (
    agent_communicate,
    get_agent_inbox,
    get_message_store,
    wait_for_agent_message,
)
from orchestrator.tools.status import create_get_task_status

logger = logging.getLogger(__name__)

SERVER_NAME = "mop"
SERVER_VERSION = "0.1.0"
SERVER_TRANSPORT = "stdio"
MCP_INSTRUCTIONS = (
    "MOP coordinates agents through one shared server process. For live "
    "cross-client messaging, every client must connect to the same Streamable "
    "HTTP endpoint. Send with agent_communicate; receive with get_agent_inbox "
    "or wait_for_agent_message. Assigning a task records ownership but does "
    "not start an agent. State is retained for the lifetime of the server."
)

_task_store = get_task_store()
_artifact_store = get_artifact_store()
_orchestrator = Orchestrator(task_store=_task_store, artifact_store=_artifact_store)

_get_task_status = create_get_task_status(_task_store)
_submit_artifact = create_submit_artifact(_artifact_store, _orchestrator)

_decompose_tool = _decompose_mod.DecomposeTool(_task_store)
_assign_tool = _assign_mod.AssignTool(_task_store, _orchestrator)
_merge_tool = _merge_mod.MergeTool(_task_store, _artifact_store)
_review_tool = _review_mod.ReviewTool(_artifact_store)

mcp = FastMCP(
    SERVER_NAME,
    version=SERVER_VERSION,
    instructions=MCP_INSTRUCTIONS,
)

mcp.tool()(_decompose_tool.decompose_task)
mcp.tool()(_assign_tool.assign_agent)
mcp.tool()(agent_communicate)
mcp.tool()(get_agent_inbox)
mcp.tool()(wait_for_agent_message)
mcp.tool()(_get_task_status)
mcp.tool()(_submit_artifact)


async def _review_code_wrapper(artifact_id: str, reviewer_agent_id: str) -> dict:
    result = await _review_tool.review_code(artifact_id, reviewer_agent_id)
    if isinstance(result, dict):
        return result
    if hasattr(result, "to_dict"):
        return result.to_dict()
    if dataclasses.is_dataclass(result):
        d = dataclasses.asdict(result)
        for key, value in d.items():
            if hasattr(value, "isoformat"):
                d[key] = value.isoformat()
            elif hasattr(value, "value"):
                d[key] = value.value
        return d
    return {}


mcp.tool()(_review_code_wrapper)
mcp.tool()(_merge_tool.merge_results)


@mcp.tool()
async def get_server_info() -> dict[str, object]:
    """Return the MOP server identity and currently registered tools."""
    try:
        registered_tools = await mcp.list_tools()
    except Exception:
        logger.exception("Unable to list registered MCP tools")
        raise

    tool_names = sorted(tool.name for tool in registered_tools)
    return {
        "name": SERVER_NAME,
        "version": SERVER_VERSION,
        "transport": SERVER_TRANSPORT,
        "live_messaging": SERVER_TRANSPORT == "streamable-http",
        "state_scope": "server_process",
        "tool_count": len(tool_names),
        "tools": tool_names,
    }


def configure_server_transport(transport: str) -> None:
    """Record the active transport reported by ``get_server_info``."""
    if transport not in {"stdio", "streamable-http"}:
        raise ValueError(f"Unsupported server transport: {transport}")

    global SERVER_TRANSPORT
    SERVER_TRANSPORT = transport


@mcp.tool()
async def register_agent(agent_id: str, name: str, model: str, role: str) -> dict:
    """Register a new agent to participate in orchestration.

    Args:
        agent_id: Unique identifier for the agent (e.g., 'D-Claude', 'E-Gemini')
        name: Human-readable name (e.g., 'Agent D (Reviewer)')
        model: LLM model identifier (e.g., 'claude-sonnet-4-6', 'gemini-2.0-flash')
        role: Agent role (e.g., 'planner', 'coder', 'tester', 'reviewer', 'analyst')

    Returns:
        The newly registered agent details.
    """
    agent = _orchestrator.add_agent(agent_id, name, model, role)
    return _agent_to_dict(agent)


@mcp.tool()
async def list_registered_agents() -> list[dict]:
    """List all registered agents available for task assignment.

    Returns:
        List of all registered agents with their details.
    """
    agents = _orchestrator.list_agents()
    return [_agent_to_dict(a) for a in agents]


def _agent_to_dict(agent: object) -> dict:
    if dataclasses.is_dataclass(agent):
        d = dataclasses.asdict(agent)
        for key, value in d.items():
            if hasattr(value, "value"):
                d[key] = value.value
        return d
    if hasattr(agent, "model_dump"):
        return agent.model_dump(mode="json")
    return {}


def _task_to_dict(task: object) -> dict:
    if dataclasses.is_dataclass(task):
        result = dataclasses.asdict(task)
        for key, value in result.items():
            if hasattr(value, "isoformat"):
                result[key] = value.isoformat()
            elif hasattr(value, "value"):
                result[key] = value.value
        return result
    if hasattr(task, "model_dump"):
        return task.model_dump(mode="json")
    return {}


def _message_to_json_dict(message: object) -> dict:
    if hasattr(message, "model_dump"):
        return message.model_dump(mode="json")
    if dataclasses.is_dataclass(message):
        d = dataclasses.asdict(message)
        for key, value in d.items():
            if hasattr(value, "isoformat"):
                d[key] = value.isoformat()
            elif hasattr(value, "value"):
                d[key] = value.value
        return d
    return {"raw": str(message)}


@mcp.resource("task://{task_id}/status")
async def task_status_resource(task_id: str) -> str:
    result = await _get_task_status(task_id)
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.resource("agent://{agent_id}/inbox")
async def agent_inbox_resource(agent_id: str) -> str:
    store = get_message_store()
    messages = store.get_inbox(agent_id)
    data = [_message_to_json_dict(m) for m in messages]
    return json.dumps(data, ensure_ascii=False, default=str)


@mcp.resource("artifact://{artifact_id}")
async def artifact_resource(artifact_id: str) -> str:
    artifact = await _artifact_store.get_artifact(artifact_id)
    if artifact is None:
        raise ValueError(f"Artifact not found: {artifact_id}")
    return json.dumps(
        artifact.model_dump(mode="json"),
        ensure_ascii=False,
        default=str,
    )


logger.info("MCP server initialized with all tools and resources")
