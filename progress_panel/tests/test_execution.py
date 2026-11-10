"""Real instruction-load receipts and honest verification, never planned activity."""

import hashlib
from pathlib import Path

import pytest

from progress_panel.server import ProgressServer
from progress_panel.skills import load_bundled_skill
from progress_panel.state import ProgressError


def start(server):
    return server.call_tool(
        "start_progress",
        {"title": "修复请求重试", "steps": [{"label": "修复", "status": "active"}]},
    )["structuredContent"]


def load(server, state, name):
    return server.call_tool(
        "load_progress_skill",
        {
            "run_id": state["run_id"],
            "expected_revision": state["revision"],
            "skill": name,
        },
    )


def test_only_actual_bundled_loads_create_receipts(tmp_path: Path):
    server = ProgressServer(tmp_path / "state")
    state = start(server)
    assert state.get("skill_loads", []) == []
    result = load(server, state, "development-workflow")
    assert not result.get("isError")
    assert "# Development Workflow" in result["content"][0]["text"]
    state = server.store.read(state["run_id"])
    receipt = state["skill_loads"][0]
    source = (
        Path(__file__).resolve().parents[2] / "skills/development-workflow/SKILL.md"
    )
    assert receipt["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert receipt["source"] == "mcp_skill_load"
    assert state["workflow"] == "development-workflow"
    retry = load(server, {**state, "revision": 1}, "development-workflow")
    assert not retry.get("isError")
    assert retry["structuredContent"]["revision"] == state["revision"]
    assert len(server.store.read(state["run_id"])["skill_loads"]) == 1
    domain = load(server, state, "systematic-debugging")
    assert not domain.get("isError")
    state = server.store.read(state["run_id"])
    assert state["workflow"] == "development-workflow"
    assert state["skill_loads"][-1]["kind"] == "skill"


def test_invalid_or_foreign_skills_cannot_claim_use(tmp_path: Path):
    server = ProgressServer(tmp_path / "state")
    state = start(server)
    for name in ("../README", "not-installed", "task-router/SKILL.md"):
        assert load(server, state, name)["isError"]
    assert server.store.read(state["run_id"])["revision"] == 1
    assert server.call_tool(
        "update_progress",
        {
            "run_id": state["run_id"],
            "expected_revision": 1,
            "status": "running",
            "steps": state["steps"],
            "details": {"skills": ["fake"]},
        },
    )["isError"]


def test_skill_file_boundary_rejects_symlinks_empty_and_oversized_instructions(
    tmp_path: Path,
):
    catalog = tmp_path / "skills"
    folder = catalog / "test-skill"
    folder.mkdir(parents=True)
    file = folder / "SKILL.md"
    for payload in (b"", b"\xff", b"x" * (128 * 1024 + 1)):
        file.write_bytes(payload)
        with pytest.raises(ProgressError):
            load_bundled_skill(catalog, "test-skill")
    file.unlink()
    outside = tmp_path / "outside.md"
    outside.write_text("external")
    file.symlink_to(outside)
    with pytest.raises(ProgressError):
        load_bundled_skill(catalog, "test-skill")


def test_loader_conflicts_are_scoped_and_cannot_overwrite_newer_workflow(
    tmp_path: Path,
):
    server = ProgressServer(tmp_path / "state")
    state = start(server)
    workflow = load(server, state, "development-workflow")["structuredContent"]
    stale = load(server, state, "finishing-development")
    assert stale["structuredContent"]["error"] == "revision_conflict"
    assert stale["structuredContent"]["current"]["run_id"] == state["run_id"]
    future = load(server, {**state, "revision": 100}, "development-workflow")
    assert future["structuredContent"]["error"] == "revision_conflict"
    assert server.store.read(state["run_id"])["revision"] == workflow["revision"]


def test_old_snapshots_without_execution_fields_survive_updates(tmp_path: Path):
    import json

    server = ProgressServer(tmp_path / "state")
    state = start(server)
    for key in ("details", "skill_loads", "workflow", "execution_mode", "method_progress"):
        state.pop(key, None)
    with server.store.connection() as connection:
        connection.execute(
            "UPDATE runs SET payload=? WHERE id=?", (json.dumps(state), state["run_id"])
        )
    assert not load(server, state, "development-workflow").get("isError")


def test_verification_independent_of_completion_and_metadata_is_preserved(
    tmp_path: Path,
):
    server = ProgressServer(tmp_path / "state")
    state = start(server)
    loaded = load(server, state, "development-workflow")["structuredContent"]
    details = {
        "current": "验证失败重试",
        "change": "已补齐幂等校验",
        "remaining": "超时恢复",
        "verification": {
            "status": "partial",
            "passed": 18,
            "pending": 2,
            "evidence": "相关回归用例结果",
        },
    }
    result = server.call_tool(
        "update_progress",
        {
            "run_id": state["run_id"],
            "expected_revision": loaded["revision"],
            "status": "running",
            "steps": state["steps"],
            "details": details,
        },
    )
    assert not result.get("isError")
    updated = server.store.read(state["run_id"])
    assert updated["details"]["verification"]["source"] == "agent_declared"
    ended = server.call_tool(
        "update_progress",
        {
            "run_id": state["run_id"],
            "expected_revision": updated["revision"],
            "status": "completed",
            "steps": [{"label": "修复", "status": "done"}],
        },
    )
    assert not ended.get("isError")
    stored = server.store.read(state["run_id"])
    assert stored["details"]["verification"]["status"] == "partial"
    assert stored["workflow"] == "development-workflow"
    assert load(server, stored, "finishing-development")["isError"]


def test_history_retains_stage_details_and_completion_clears_stale_actions(tmp_path: Path):
    server = ProgressServer(tmp_path / "state")
    state = start(server)
    first_details = {
        "current": "验证重试",
        "change": "补齐幂等校验",
        "remaining": "超时恢复",
        "verification": {"status": "partial", "evidence": "超时场景尚未验证"},
    }
    server.call_tool("update_progress", {
        "run_id": state["run_id"], "expected_revision": 1,
        "status": "running", "steps": state["steps"], "details": first_details,
    })
    server.call_tool("update_progress", {
        "run_id": state["run_id"], "expected_revision": 2,
        "status": "completed", "steps": [{"label": "修复", "status": "done"}],
    })
    stored = server.store.read(state["run_id"])
    previous = stored["history"][-2]
    assert previous["details"]["change"] == "补齐幂等校验"
    assert previous["current_step"] == "修复"
    assert previous["details"]["verification"]["status"] == "partial"
    assert "current" not in stored["details"]
    assert "remaining" not in stored["details"]
    assert stored["details"]["verification"]["status"] == "partial"
    retry = server.call_tool("update_progress", {
        "run_id": state["run_id"], "expected_revision": 2,
        "status": "completed", "steps": [{"label": "修复", "status": "done"}],
    })
    assert not retry.get("isError")
    assert server.store.read(state["run_id"])["revision"] == 3


def test_waiting_reason_is_validated_and_cleared_when_work_resumes(tmp_path: Path):
    server = ProgressServer(tmp_path / "state")
    state = start(server)
    arguments = {
        "run_id": state["run_id"], "expected_revision": 1,
        "status": "waiting", "steps": state["steps"],
        "details": {"waiting_for": "external", "reason": "等待构建结果"},
    }
    result = server.call_tool("update_progress", arguments)
    assert not result.get("isError")
    waiting = server.store.read(state["run_id"])
    assert waiting["details"]["waiting_for"] == "external"
    assert waiting["history"][-1]["details"]["reason"] == "等待构建结果"
    server.call_tool("update_progress", {
        "run_id": state["run_id"], "expected_revision": 2,
        "status": "running", "steps": state["steps"],
    })
    resumed = server.store.read(state["run_id"])
    assert "waiting_for" not in resumed["details"]
    assert "reason" not in resumed["details"]
    result = server.call_tool("update_progress", {
        **arguments, "expected_revision": 3, "details": {"waiting_for": "invented"},
    })
    assert result["isError"]


@pytest.mark.parametrize(
    "verification",
    [
        {"status": "passed", "failed": 1, "evidence": "check"},
        {"status": "not_run", "passed": 1, "evidence": "check"},
        {"status": "passed", "passed": True, "evidence": "check"},
        {"status": "passed", "passed": 2},
        {"status": "passed", "passed": -1, "evidence": "check"},
    ],
)
def test_invalid_test_counts_never_reach_storage(tmp_path: Path, verification):
    server = ProgressServer(tmp_path / "state")
    state = start(server)
    result = server.call_tool(
        "update_progress",
        {
            "run_id": state["run_id"],
            "expected_revision": 1,
            "status": "running",
            "steps": state["steps"],
            "details": {"verification": verification},
        },
    )
    assert result["isError"]
    assert server.store.read(state["run_id"])["revision"] == 1
