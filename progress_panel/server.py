"""MCP stdio endpoint for task-scoped progress. No network or runtime dependencies."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from progress_panel.skills import load_bundled_skill
from progress_panel.state import SKILL_ID_PATTERN, SKILL_USE_VIAS, ProgressError, ProgressStore

RESOURCE_URI = "ui://relayforge-development/progress-v2.html"
MAX_REQUEST_BYTES = 16 * 1024
STEP_SCHEMA: dict[str, Any] = {
    "type": "array",
    "minItems": 1,
    "maxItems": 12,
    "items": {
        "type": "object",
        "additionalProperties": False,
        "required": ["label", "status"],
        "properties": {
            "label": {"type": "string", "minLength": 1, "maxLength": 80},
            "status": {
                "type": "string",
                "enum": ["pending", "active", "done", "blocked", "skipped"],
            },
        },
    },
}
ID_SCHEMA = {"type": "string", "format": "uuid"}
MODE_SCHEMA = {"type": "string", "enum": ["L1", "L2", "L3"]}
SKILL_USES_SCHEMA = {
    "type": "array", "maxItems": 32,
    "description": "Add only Skills actually read and used for this task, including external and direct reads. These are Agent declarations, not tool-load receipts. Omission preserves prior records.",
    "items": {
        "type": "object", "additionalProperties": False,
        "required": ["skill", "via"],
        "properties": {
            "skill": {"type": "string", "pattern": SKILL_ID_PATTERN,
                      "description": "namespace:skill-name from the real catalog (host:name for personal/system Skills; project:name for project Skills; plugin-name:name for plugin Skills). Bare names mean host:name."},
            "via": {"type": "string", "enum": sorted(SKILL_USE_VIAS),
                    "description": "direct_read: read instruction file; skill_tool: selected via a Skill tool; context: instructions supplied by host and actually applied. Never metadata discovery or planned use."},
        },
    },
}
METHOD_PROGRESS_SCHEMA = {
    "type": "array", "maxItems": 3,
    "items": {
        "type": "object", "additionalProperties": False,
        "required": ["method", "status", "phases"],
        "properties": {
            "method": {"type": "string", "enum": ["sdd", "tdd", "coordination"]},
            "status": {"type": "string", "enum": ["running", "waiting", "completed", "blocked", "cancelled"]},
            "phases": {**STEP_SCHEMA, "maxItems": 8, "items": {
                **STEP_SCHEMA["items"], "properties": {
                    **STEP_SCHEMA["items"]["properties"],
                    "label": {"type": "string", "minLength": 1, "maxLength": 40},
                },
            }},
        },
    },
}
SUMMARY_SCHEMA = {"type": "string", "maxLength": 240}
DETAILS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        **{
            key: {"type": "string", "maxLength": 120}
            for key in ("current", "change", "remaining", "reason")
        },
        "waiting_for": {"type": "string", "enum": ["user", "external"]},
        "verification": {
            "type": "object",
            "additionalProperties": False,
            "required": ["status"],
            "properties": {
                "status": {
                    "type": "string",
                    "enum": [
                        "not_run",
                        "running",
                        "passed",
                        "failed",
                        "partial",
                        "skipped",
                        "unavailable",
                    ],
                },
                **{
                    key: {"type": "integer", "minimum": 0, "maximum": 1000000}
                    for key in ("passed", "failed", "pending")
                },
                "evidence": {"type": "string", "maxLength": 120},
            },
        },
    },
}


def schema(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    """Build a closed tool schema so arbitrary payload fields are never accepted."""
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def tools() -> list[dict[str, Any]]:
    """Describe render and data tools separately; only reads are app-only."""
    renderer = {
        "ui": {"resourceUri": RESOURCE_URI, "visibility": ["model", "app"]},
    }
    definitions = [
        (
            "start_progress",
            "创建开发进度卡片",
            "Start and display development progress. Declare execution_mode L1/L2/L3 once selected, method_progress for selected SDD/TDD/coordination phases, and details.current for the concrete action. Never infer phases from skill loads or send raw prompts, code, commands or logs.",
            schema(
                {
                    "title": {"type": "string", "minLength": 1, "maxLength": 80},
                    "steps": STEP_SCHEMA,
                    "summary": SUMMARY_SCHEMA,
                    "details": DETAILS_SCHEMA,
                    "execution_mode": MODE_SCHEMA,
                    "method_progress": METHOD_PROGRESS_SCHEMA,
                    "skill_uses": SKILL_USES_SCHEMA,
                },
                ["title", "steps"],
            ),
            False,
            False,
            renderer,
        ),
        (
            "update_progress",
            "更新开发进度",
            "Update a real milestone using run_id and revision. Keep execution_mode independent of loaded workflow; replace method_progress when selected method phases advance. Omission preserves declarations; ending a task requires ending its method tracks explicitly. Never invent percentages. A revision conflict returns the scoped snapshot.",
            schema(
                {
                    "run_id": ID_SCHEMA,
                    "expected_revision": {"type": "integer", "minimum": 1},
                    "status": {
                        "type": "string",
                        "enum": [
                            "running",
                            "waiting",
                            "completed",
                            "blocked",
                            "cancelled",
                        ],
                    },
                    "steps": STEP_SCHEMA,
                    "summary": SUMMARY_SCHEMA,
                    "details": DETAILS_SCHEMA,
                    "execution_mode": MODE_SCHEMA,
                    "method_progress": METHOD_PROGRESS_SCHEMA,
                    "skill_uses": SKILL_USES_SCHEMA,
                },
                ["run_id", "expected_revision", "status", "steps"],
            ),
            False,
            True,
            {},
        ),
        (
            "load_progress_skill",
            "加载并记录 Skill",
            "Read this plugin's bundled SKILL.md and record a real instruction-load receipt for this run. Apply the returned instructions. Use only when the skill is actually selected; never load planned skills just to fill the card. Loaded is not an execution or success audit. Core workflow loads also select the current workflow. Reuse the returned revision; avoid reloading the same unchanged skill.",
            schema(
                {
                    "run_id": ID_SCHEMA,
                    "expected_revision": {"type": "integer", "minimum": 1},
                    "skill": {"type": "string", "pattern": "^[a-z0-9][a-z0-9-]{0,63}$"},
                },
                ["run_id", "expected_revision", "skill"],
            ),
            False,
            True,
            {"ui": {"visibility": ["model"]}},
        ),
        (
            "open_progress",
            "重新显示进度卡片",
            "Reopen an existing task panel only when requested; requires that task's run_id. Does not create or restart work.",
            schema({"run_id": ID_SCHEMA}, ["run_id"]),
            True,
            True,
            renderer,
        ),
        (
            "read_progress",
            "读取当前进度",
            "Read exactly the task bound to this panel; no latest-task fallback or access to logs.",
            schema({"run_id": ID_SCHEMA}, ["run_id"]),
            True,
            True,
            {"ui": {"visibility": ["app"]}},
        ),
    ]
    return [
        {
            "name": name,
            "title": title,
            "description": description,
            "inputSchema": input_schema,
            "annotations": {
                "readOnlyHint": read_only,
                "destructiveHint": False,
                "idempotentHint": idempotent,
                "openWorldHint": False,
            },
            "_meta": meta,
        }
        for name, title, description, input_schema, read_only, idempotent, meta in definitions
    ]


@dataclass
class RpcError(ValueError):
    """A JSON-RPC error that never includes the caller's input."""

    code: int
    message: str


def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject ambiguous duplicate JSON keys, including nested tool arguments."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def invalid_constant(_: str) -> None:
    """JSON NaN and Infinity are not valid protocol values."""
    raise ValueError("invalid_json_constant")


class ProgressServer:
    """Handle synchronous, bounded MCP requests; SQLite serializes shared writers."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._store: ProgressStore | None = None

    @property
    def store(self) -> ProgressStore:
        """Create private state only when a tool actually needs it."""
        if self._store is None:
            self._store = ProgressStore(self.directory)
        return self._store

    def call_tool(self, name: object, arguments: object) -> dict[str, Any]:
        """Validate closed arguments, then perform only the declared task operation."""
        try:
            definition = next((item for item in tools() if item["name"] == name), None)
            if definition is None:
                raise ProgressError("unknown_tool")
            if not isinstance(arguments, dict):
                raise ProgressError("invalid_arguments")
            spec = definition["inputSchema"]
            if set(arguments) - set(spec["properties"]) or set(spec["required"]) - set(
                arguments
            ):
                raise ProgressError("invalid_arguments")
            if "execution_mode" in arguments and arguments["execution_mode"] is None:
                raise ProgressError("invalid_execution_mode")
            if "method_progress" in arguments and arguments["method_progress"] is None:
                raise ProgressError("invalid_method_progress")
            if "skill_uses" in arguments and arguments["skill_uses"] is None:
                raise ProgressError("invalid_skill_uses")
            if name == "start_progress":
                state = self.store.start(
                    arguments["title"],
                    arguments["steps"],
                    arguments.get("summary", ""),
                    arguments.get("details"),
                    execution_mode=arguments.get("execution_mode"),
                    declared_methods=arguments.get("method_progress"),
                    used_skills=arguments.get("skill_uses"),
                )
            elif name == "update_progress":
                state = self.store.update(
                    arguments["run_id"],
                    arguments["expected_revision"],
                    arguments["status"],
                    arguments["steps"],
                    arguments.get("summary", ""),
                    arguments.get("details"),
                    execution_mode=arguments.get("execution_mode"),
                    declared_methods=arguments.get("method_progress"),
                    used_skills=arguments.get("skill_uses"),
                )
            elif name == "load_progress_skill":
                current = self.store.read(arguments["run_id"])
                if current["status"] in {"completed", "blocked", "cancelled"}:
                    raise ProgressError("run_ended")
                loaded = load_bundled_skill(
                    Path(__file__).resolve().parent.parent / "skills",
                    arguments["skill"],
                )
                state = self.store.record_skill_load(
                    arguments["run_id"],
                    arguments["expected_revision"],
                    loaded.name,
                    loaded.digest,
                    loaded.is_workflow,
                )
                return {
                    "structuredContent": {
                        "run_id": state["run_id"],
                        "revision": state["revision"],
                        "loaded_skill": loaded.name,
                        "source": "mcp_skill_load",
                    },
                    "content": [{"type": "text", "text": loaded.instructions}],
                }
            else:
                state = self.store.read(arguments["run_id"])
            if name == "update_progress":
                state = {
                    key: state[key]
                    for key in ("run_id", "revision", "status", "updated_at")
                }
            return {
                "structuredContent": state,
                "content": [
                    {"type": "text", "text": json.dumps(state, ensure_ascii=False)}
                ],
            }
        except ProgressError as error:
            data: dict[str, Any] = {"error": error.code}
            if error.current is not None:
                data["current"] = error.current
            return {
                "isError": True,
                "structuredContent": data,
                "content": [{"type": "text", "text": error.code}],
            }
        except (OSError, sqlite3.Error):
            return {
                "isError": True,
                "content": [{"type": "text", "text": "storage_unavailable"}],
            }

    def dispatch(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Implement MCP discovery, tools and the one packaged UI resource."""
        if method == "initialize":
            requested = params.get("protocolVersion")
            supported = {"2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"}
            version = json.loads(
                (Path(__file__).resolve().parent.parent / "plugin.json").read_text()
            )["version"]
            return {
                "protocolVersion": (
                    requested if requested in supported else "2025-11-25"
                ),
                "capabilities": {"tools": {}, "resources": {}},
                "serverInfo": {"name": "relayforge-progress", "version": version},
                "instructions": (
                    "For software development tasks using RelayForge, call start_progress once "
                    "before substantive work, then update_progress at meaningful milestones and "
                    "the actual final outcome. Use load_progress_skill only for selected bundled "
                    "skills to deliver their instructions and record actual loads. Report every other "
                    "actually used Skill in skill_uses on start_progress/update_progress "
                    "after reading/applying it, including external, direct-read and host-provided instructions. "
                    "Use namespace:skill-name with direct_read/skill_tool/context; never report planned or "
                    "merely discovered Skills. Declarations are not load receipts or execution audits. Retain "
                    "the run_id and revision returned by every write tool. Prefer concise current/change/remaining "
                    "details and evidence-supported verification; never infer a test pass from task completion. "
                    "Once routing is selected declare execution_mode L1/L2/L3. Keep SDD/TDD/coordination "
                    "method_progress phases explicit and details.current concrete; skill loads never "
                    "change the mode or prove method progress. Preserve mode across finishing. "
                    "Send only short agent-declared steps; never raw prompts, code, commands, "
                    "credentials or logs. Do not create panels for unrelated questions. "
                    "Unavailable progress must not block the requested development work."
                ),
            }
        if method in {"ping", "resources/templates/list"}:
            return {"resourceTemplates": []} if method != "ping" else {}
        if method == "tools/list":
            return {"tools": tools()}
        if method == "tools/call":
            return self.call_tool(params.get("name"), params.get("arguments", {}))
        if method == "resources/list":
            return {
                "resources": [
                    {
                        "uri": RESOURCE_URI,
                        "name": "relayforge-progress-panel",
                        "mimeType": "text/html;profile=mcp-app",
                    }
                ]
            }
        if method == "resources/read":
            if params.get("uri") != RESOURCE_URI:
                raise RpcError(-32602, "unknown_resource")
            html = (Path(__file__).parent / "static/panel.html").read_text(
                encoding="utf-8"
            )
            return {
                "contents": [
                    {
                        "uri": RESOURCE_URI,
                        "mimeType": "text/html;profile=mcp-app",
                        "text": html,
                        "_meta": {
                            "ui": {
                                "prefersBorder": False,
                                "csp": {"connectDomains": [], "resourceDomains": []},
                            },
                            "openai/ui": {"availableDisplayModes": ["inline"]},
                        },
                    }
                ]
            }
        raise RpcError(-32601, "method_not_found")

    def serve(self, source: BinaryIO, target: BinaryIO) -> None:
        """Serve newline-delimited JSON-RPC with size limits and silent notifications."""
        while line := source.readline(MAX_REQUEST_BYTES + 1):
            identifier: str | int | None = None
            try:
                if len(line) > MAX_REQUEST_BYTES:
                    while line and not line.endswith(b"\n"):
                        line = source.readline(MAX_REQUEST_BYTES + 1)
                    raise RpcError(-32600, "request_too_large")
                value = json.loads(
                    line,
                    object_pairs_hook=no_duplicates,
                    parse_constant=invalid_constant,
                )
                if not isinstance(value, dict) or value.get("jsonrpc") != "2.0":
                    raise RpcError(-32600, "invalid_request")
                raw_id = value.get("id")
                if raw_id is not None and type(raw_id) not in {str, int}:
                    raise RpcError(-32600, "invalid_request_id")
                identifier = raw_id
                if "id" not in value:
                    continue
                method, params = value.get("method"), value.get("params", {})
                if not isinstance(method, str) or not isinstance(params, dict):
                    raise RpcError(-32600, "invalid_request")
                result = self.dispatch(method, params)
                response = {"jsonrpc": "2.0", "id": identifier, "result": result}
            except (ValueError, UnicodeDecodeError) as error:
                code, message = (
                    (error.code, error.message)
                    if isinstance(error, RpcError)
                    else (-32700, "parse_error")
                )
                response = {
                    "jsonrpc": "2.0",
                    "id": identifier,
                    "error": {"code": code, "message": message},
                }
            except (OSError, sqlite3.Error, TypeError):
                response = {
                    "jsonrpc": "2.0",
                    "id": identifier,
                    "error": {"code": -32603, "message": "service_unavailable"},
                }
            target.write(
                (json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8")
            )
            target.flush()


def data_directory() -> Path:
    """Use host-managed data when supplied, otherwise a separate local state folder."""
    override = os.environ.get("RELAYFORGE_PROGRESS_DATA_DIR")
    if override:
        return Path(override).expanduser()
    managed = os.environ.get("PLUGIN_DATA") or os.environ.get("CLAUDE_PLUGIN_DATA")
    if managed:
        return Path(managed).expanduser() / "progress-panel"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/RelayForge/progress-panel"
    if os.name == "nt":
        return (
            Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
            / "RelayForge/progress-panel"
        )
    return (
        Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
        / "relayforge-development/progress-panel"
    )


def main() -> None:
    """Start a foreground stdio server; errors never print input or credentials."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=None)
    arguments = parser.parse_args()
    ProgressServer(arguments.data_dir or data_directory()).serve(
        sys.stdin.buffer, sys.stdout.buffer
    )


if __name__ == "__main__":
    main()
