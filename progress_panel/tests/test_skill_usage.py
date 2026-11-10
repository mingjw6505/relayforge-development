"""External and direct-read usage is declared separately from real load receipts."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from progress_panel.server import ProgressServer


def usage(skill="host:imagegen", via="direct_read"):
    return {"skill": skill, "via": via}


def start(server, **extra):
    return server.call_tool(
        "start_progress",
        {
            "title": "Skill records",
            "steps": [{"label": "Implement", "status": "active"}],
            **extra,
        },
    )


def update(server, state, **extra):
    return server.call_tool(
        "update_progress",
        {
            "run_id": state["run_id"],
            "expected_revision": state["revision"],
            "status": "running",
            "steps": state["steps"],
            **extra,
        },
    )


def test_external_direct_and_host_use_have_explicit_declaration_provenance(
    tmp_path: Path,
):
    server = ProgressServer(tmp_path / "state")
    result = start(
        server,
        skill_uses=[
            usage(),
            usage("other-plugin:design", "skill_tool"),
            usage("host:openai-docs", "context"),
        ],
    )
    assert not result.get("isError"), result
    state = result["structuredContent"]
    assert [entry["skill"] for entry in state["skill_uses"]] == [
        "host:imagegen",
        "other-plugin:design",
        "host:openai-docs",
    ]
    assert all(
        entry["source"] == "agent_declared" and entry["recorded_at"]
        for entry in state["skill_uses"]
    )
    assert all("sha256" not in entry for entry in state["skill_uses"])
    assert state["skill_loads"] == [] and state["workflow"] is None
    assert state["history"][0]["skill_uses"] == state["skill_uses"]


def test_incremental_uses_preserve_namespaces_channels_and_retry_safety(tmp_path: Path):
    server = ProgressServer(tmp_path / "state")
    first = start(server, skill_uses=[usage("frontend-design")])["structuredContent"]
    result = update(
        server,
        first,
        skill_uses=[
            usage("host:frontend-design"),
            usage("relayforge-development:frontend-design"),
            usage("host:frontend-design", "skill_tool"),
        ],
    )
    assert not result.get("isError"), result
    current = server.store.read(first["run_id"])
    assert len(current["skill_uses"]) == 3
    assert current["skill_uses"][0]["skill"] == "host:frontend-design"
    assert len(current["history"][-1]["skill_uses"]) == 2
    assert (
        update(
            server,
            first,
            skill_uses=[
                usage("host:frontend-design"),
                usage("relayforge-development:frontend-design"),
                usage("host:frontend-design", "skill_tool"),
            ],
        )["structuredContent"]["revision"]
        == current["revision"]
    )
    assert server.store.read(first["run_id"]) == current
    update(server, current, summary="Next milestone")
    later = server.store.read(first["run_id"])
    assert later["skill_uses"] == current["skill_uses"]
    assert "skill_uses" not in later["history"][-1]


def test_declarations_do_not_create_load_receipts_or_select_workflow(tmp_path: Path):
    server = ProgressServer(tmp_path / "state")
    state = start(server)["structuredContent"]
    loaded = server.call_tool(
        "load_progress_skill",
        {"run_id": state["run_id"], "expected_revision": 1, "skill": "task-router"},
    )
    assert not loaded.get("isError")
    state = server.store.read(state["run_id"])
    previous = state["skill_loads"]
    assert not update(
        server,
        state,
        skill_uses=[
            usage("relayforge-development:task-router"),
            usage("relayforge-development:finishing-development"),
        ],
    ).get("isError")
    current = server.store.read(state["run_id"])
    assert current["skill_loads"] == previous
    assert current["workflow"] == "task-router"


@pytest.mark.parametrize(
    "value",
    [
        None,
        True,
        {},
        ["imagegen"],
        [usage("")],
        [usage("../SKILL.md")],
        [usage("/private/skill")],
        [usage("x:y:z")],
        [usage("host:secret\n")],
        [usage(via="planned")],
        [usage(via="mcp_skill_load")],
        [{**usage(), "source": "host_observed"}],
        [{**usage(), "sha256": "a" * 64}],
        [{**usage(), "path": "/secret"}],
        [usage(), usage()],
        [usage(f"host:skill-{n}") for n in range(33)],
    ],
)
def test_invalid_or_forged_usage_leaves_current_run_unchanged(tmp_path: Path, value):
    server = ProgressServer(tmp_path / "state")
    state = start(server)["structuredContent"]
    result = update(server, state, skill_uses=value)
    assert result.get("isError"), result
    assert server.store.read(state["run_id"]) == state
    assert "secret" not in str(result.get("content"))


def test_usage_is_task_scoped_bounded_and_terminal_records_are_immutable(
    tmp_path: Path,
):
    server = ProgressServer(tmp_path / "state")
    first = start(server, skill_uses=[usage(f"host:skill-{n}") for n in range(32)])[
        "structuredContent"
    ]
    second = start(server)["structuredContent"]
    assert second["skill_uses"] == []
    update(server, first, skill_uses=[usage(f"host:skill-{n}") for n in range(32, 64)])
    current = server.store.read(first["run_id"])
    assert len(current["skill_uses"]) == 64
    assert (
        update(server, current, skill_uses=[usage("host:overflow")])[
            "structuredContent"
        ]["error"]
        == "skill_use_limit"
    )
    assert server.store.read(first["run_id"]) == current
    assert server.store.read(second["run_id"]) == second
    done = [{"label": "Implement", "status": "done"}]
    update(server, current, status="completed", steps=done)
    ended = server.store.read(first["run_id"])
    result = update(
        server, ended, status="completed", steps=done, skill_uses=[usage("host:late")]
    )
    assert result["structuredContent"]["error"] == "run_ended"
    assert server.store.read(first["run_id"]) == ended


def test_concurrent_usage_updates_require_revision_reconciliation(tmp_path: Path):
    server = ProgressServer(tmp_path / "state")
    state = start(server)["structuredContent"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda name: update(
                    ProgressServer(server.directory), state, skill_uses=[usage(name)]
                ),
                ["host:one", "host:two"],
            )
        )
    assert sum(bool(result.get("isError")) for result in results) == 1
    assert (
        next(result for result in results if result.get("isError"))[
            "structuredContent"
        ]["error"]
        == "revision_conflict"
    )
    current = server.store.read(state["run_id"])
    assert len(current["skill_uses"]) == 1
    missing = (
        "host:two" if current["skill_uses"][0]["skill"] == "host:one" else "host:one"
    )
    assert not update(server, current, skill_uses=[usage(missing)]).get("isError")
    assert len(server.store.read(state["run_id"])["skill_uses"]) == 2


def test_legacy_snapshots_accept_new_usage_without_reconstructing_history(
    tmp_path: Path,
):
    import json

    server = ProgressServer(tmp_path / "state")
    state = start(server)["structuredContent"]
    state.pop("skill_uses")
    with server.store.connection() as connection:
        connection.execute(
            "UPDATE runs SET payload=? WHERE id=?", (json.dumps(state), state["run_id"])
        )
    assert not update(server, state, skill_uses=[usage()]).get("isError")
    current = server.store.read(state["run_id"])
    assert current["skill_uses"][0]["skill"] == "host:imagegen"
    assert "skill_uses" not in current["history"][0]
    assert current["history"][-1]["skill_uses"] == current["skill_uses"]
    update(server, current, skill_uses=[])
    assert server.store.read(state["run_id"])["skill_uses"] == current["skill_uses"]


def test_discovery_exposes_optional_closed_usage_schema_on_both_write_tools(
    tmp_path: Path,
):
    server = ProgressServer(tmp_path / "state")
    definitions = {
        tool["name"]: tool for tool in server.dispatch("tools/list", {})["tools"]
    }
    for name in ("start_progress", "update_progress"):
        schema = definitions[name]["inputSchema"]
        assert "skill_uses" not in schema["required"]
        item = schema["properties"]["skill_uses"]["items"]
        assert item["additionalProperties"] is False
        assert set(item["properties"]) == {"skill", "via"}
    assert "skill_uses" in server.dispatch("initialize", {})["instructions"]
    assert not server.directory.exists()
