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
from orchestrator.tools.communicate import agent_communicate, get_message_store
from orchestrator.tools.status import create_get_task_status

logger = logging.getLogger(__name__)

_task_store = get_task_store()
_artifact_store = get_artifact_store()
_orchestrator = Orchestrator(task_store=_task_store, artifact_store=_artifact_store)

_get_task_status = create_get_task_status(_task_store)
_submit_artifact = create_submit_artifact(_artifact_store, _orchestrator)

_decompose_tool = _decompose_mod.DecomposeTool(_task_store)
_assign_tool = _assign_mod.AssignTool(_task_store, _orchestrator)
_merge_tool = _merge_mod.MergeTool(_task_store, _artifact_store)
_review_tool = _review_mod.ReviewTool(_artifact_store)

mcp = FastMCP("mop")

mcp.tool()(_decompose_tool.decompose_task)
mcp.tool()(_assign_tool.assign_agent)
mcp.tool()(agent_communicate)
mcp.tool()(_get_task_status)
mcp.tool()(_submit_artifact)
mcp.tool()(_review_tool.review_code)
mcp.tool()(_merge_tool.merge_results)


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


@mcp.resource("task://{task_id}/status")
async def task_status_resource(task_id: str) -> str:
    result = await _get_task_status(task_id)
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.resource("agent://{agent_id}/inbox")
async def agent_inbox_resource(agent_id: str) -> str:
    store = get_message_store()
    messages = store.get_inbox(agent_id)
    return json.dumps(messages, ensure_ascii=False, default=str)


@mcp.resource("artifact://{artifact_id}")
async def artifact_resource(artifact_id: str) -> str:
    artifact = await _artifact_store.get_artifact(artifact_id)
    if artifact is None:
        raise ValueError(f"Artifact not found: {artifact_id}")
    return json.dumps(
        artifact.model_dump(mode="json"), ensure_ascii=False, default=str,
    )


logger.info("MCP server initialized with all tools and resources")
