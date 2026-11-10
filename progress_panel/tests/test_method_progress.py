"""Execution mode, selected methods and concrete work remain separate declarations."""

from pathlib import Path

import pytest

from progress_panel.server import ProgressServer


def declaration():
    return {
        "title": "完善重试机制",
        "execution_mode": "L2",
        "method_progress": [{
            "method": "sdd", "status": "running",
            "phases": [
                {"label": "规格文档", "status": "active"},
                {"label": "实施计划", "status": "pending"},
                {"label": "实现与验证", "status": "pending"},
            ],
        }],
        "steps": [{"label": "编写规格", "status": "active"}],
        "details": {"current": "正在生成规格文档"},
    }


def test_mode_method_phases_and_current_work_survive_workflow_loads(tmp_path: Path):
    server = ProgressServer(tmp_path / "panel")
    result = server.call_tool("start_progress", declaration())
    assert not result.get("isError")
    state = result["structuredContent"]
    assert state["execution_mode"] == "L2"
    assert state["method_progress"][0]["phases"][0]["label"] == "规格文档"
    assert state["method_progress"][0]["source"] == "agent_declared"
    assert state["details"]["current"] == "正在生成规格文档"
    assert state["history"][0]["execution_mode"] == "L2"
    result = server.call_tool("load_progress_skill", {
        "run_id": state["run_id"], "expected_revision": 1, "skill": "finishing-development",
    })
    assert not result.get("isError")
    state = server.store.read(state["run_id"])
    assert state["workflow"] == "finishing-development"
    assert state["execution_mode"] == "L2"
    assert state["method_progress"][0]["status"] == "running"


def test_method_updates_are_historical_and_omission_preserves_them(tmp_path: Path):
    server = ProgressServer(tmp_path / "panel")
    state = server.call_tool("start_progress", declaration())["structuredContent"]
    progress = [{"method": "sdd", "status": "running", "phases": [
        {"label": "规格文档", "status": "done"},
        {"label": "实施计划", "status": "active"},
        {"label": "实现与验证", "status": "pending"},
    ]}]
    args = {"run_id": state["run_id"], "expected_revision": 1,
            "status": "running", "steps": state["steps"], "method_progress": progress}
    assert not server.call_tool("update_progress", args).get("isError")
    assert not server.call_tool("update_progress", args).get("isError")
    state = server.store.read(state["run_id"])
    assert state["revision"] == 2
    assert state["history"][0]["method_progress"][0]["phases"][0]["status"] == "active"
    assert state["history"][-1]["method_progress"][0]["phases"][0]["status"] == "done"
    assert not server.call_tool("update_progress", {
        "run_id": state["run_id"], "expected_revision": 2,
        "status": "running", "steps": state["steps"], "execution_mode": "L3",
    }).get("isError")
    state = server.store.read(state["run_id"])
    assert state["execution_mode"] == "L3"
    assert state["method_progress"][0]["phases"] == progress[0]["phases"]


def test_completion_cannot_leave_method_phases_running(tmp_path: Path):
    server = ProgressServer(tmp_path / "panel")
    state = server.call_tool("start_progress", declaration())["structuredContent"]
    args = {"run_id": state["run_id"], "expected_revision": 1,
            "status": "completed", "steps": [{"label": "编写规格", "status": "done"}]}
    assert server.call_tool("update_progress", args)["isError"]
    finished = declaration()["method_progress"]
    finished[0]["status"] = "completed"
    for phase in finished[0]["phases"]:
        phase["status"] = "done"
    assert not server.call_tool("update_progress", {**args, "method_progress": finished}).get("isError")
    state = server.store.read(state["run_id"])
    assert state["method_progress"][0]["status"] == "completed"
    assert "verification" not in state["details"]


@pytest.mark.parametrize("change", [
    {"execution_mode": "L4"},
    {"execution_mode": None},
    {"method_progress": None},
    {"method_progress": [{"method": "sdd", "status": "running", "phases": []}]},
    {"method_progress": [{"method": "invented", "status": "running", "phases": [{"label": "X", "status": "active"}]}]},
    {"method_progress": [{"method": "sdd", "status": "completed", "phases": [{"label": "X", "status": "active"}]}]},
    {"method_progress": [{**declaration()["method_progress"][0], "source": "host_verified"}]},
])
def test_invalid_mode_or_method_is_rejected(tmp_path: Path, change):
    server = ProgressServer(tmp_path / "panel")
    assert server.call_tool("start_progress", {**declaration(), **change})["isError"]


def test_legacy_start_does_not_infer_mode_or_methods(tmp_path: Path):
    server = ProgressServer(tmp_path / "panel")
    args = declaration()
    args.pop("execution_mode")
    args.pop("method_progress")
    state = server.call_tool("start_progress", args)["structuredContent"]
    assert state.get("execution_mode") is None
    assert state.get("method_progress", []) == []


def test_mode_transitions_are_adjacent_and_stale_writes_return_scoped_conflicts(tmp_path: Path):
    server = ProgressServer(tmp_path / "panel")
    args = {**declaration(), "execution_mode": "L1", "method_progress": []}
    state = server.call_tool("start_progress", args)["structuredContent"]
    update = {"run_id": state["run_id"], "expected_revision": 1,
              "status": "running", "steps": state["steps"]}
    assert server.call_tool("update_progress", {**update, "execution_mode": "L3"})["isError"]
    assert not server.call_tool("update_progress", {**update, "execution_mode": "L2"}).get("isError")
    assert not server.call_tool("update_progress", {**update, "expected_revision": 2, "execution_mode": "L3"}).get("isError")
    conflict = server.call_tool("update_progress", {**update, "execution_mode": "L1"})
    assert conflict["structuredContent"]["error"] == "revision_conflict"
    assert conflict["structuredContent"]["current"]["execution_mode"] == "L3"


@pytest.mark.parametrize("progress", [
    declaration()["method_progress"] * 2,
    [{"method": "sdd", "status": "running", "phases": [
        {"label": str(index), "status": "active" if index == 0 else "pending"}
        for index in range(9)
    ]}],
    [{"method": "sdd", "status": "running", "phases": [{"label": "x" * 41, "status": "active"}]}],
    [{"method": "sdd", "status": "running", "phases": [{"label": "A", "status": "active"}, {"label": "B", "status": "active"}]}],
])
def test_method_phases_stay_bounded_and_unambiguous(tmp_path: Path, progress):
    server = ProgressServer(tmp_path / "panel")
    assert server.call_tool("start_progress", {**declaration(), "method_progress": progress})["isError"]
