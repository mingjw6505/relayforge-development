"""Public state transitions and task isolation for the bundled progress panel."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from progress_panel.state import ProgressError, ProgressStore


@pytest.fixture
def store(tmp_path: Path) -> ProgressStore:
    return ProgressStore(tmp_path / "panel")


def initial_steps() -> list[dict[str, str]]:
    return [
        {"label": "实现", "status": "active"},
        {"label": "验证", "status": "pending"},
    ]


def test_task_lifecycle_persists_and_rejects_false_completion(
    store: ProgressStore,
) -> None:
    run = store.start("开发任务", initial_steps(), "开始实现")
    assert run["revision"] == 1
    with pytest.raises(ProgressError, match="incomplete_steps"):
        store.update(run["run_id"], 1, "completed", initial_steps(), "完成")
    next_steps = [
        {"label": "实现", "status": "done"},
        {"label": "验证", "status": "active"},
    ]
    updated = store.update(run["run_id"], 1, "running", next_steps, "正在验证")
    assert updated["revision"] == 2
    assert ProgressStore(store.directory).read(run["run_id"]) == updated
    # Lost-response retries must not append another event or advance revision.
    assert store.update(run["run_id"], 1, "running", next_steps, "正在验证") == updated
    done = [{"label": step["label"], "status": "done"} for step in next_steps]
    ended = store.update(run["run_id"], 2, "completed", done, "验证通过")
    assert ended["status"] == "completed"
    with pytest.raises(ProgressError, match="run_ended"):
        store.update(run["run_id"], 3, "running", initial_steps(), "重新开始")


def test_runs_never_fall_back_to_latest_or_change_other_tasks(
    store: ProgressStore,
) -> None:
    first = store.start("任务一", initial_steps(), "")
    second = store.start("任务二", initial_steps(), "")
    store.update(
        first["run_id"],
        1,
        "blocked",
        [{"label": "实现", "status": "blocked"}],
        "需要外部信息",
    )
    assert store.read(second["run_id"]) == second
    with pytest.raises(ProgressError, match="unknown_run"):
        store.read("00000000-0000-4000-8000-000000000000")
    with pytest.raises(ProgressError, match="invalid_run_id"):
        store.read("../../config.toml")


def test_concurrent_updates_cannot_overwrite_newer_progress(
    store: ProgressStore,
) -> None:
    run = store.start("开发任务", initial_steps(), "")

    def update(summary: str) -> str:
        try:
            ProgressStore(store.directory).update(
                run["run_id"], 1, "waiting", initial_steps(), summary
            )
            return "updated"
        except ProgressError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(update, ["等待输入一", "等待输入二"]))
    assert sorted(outcomes) == ["revision_conflict", "updated"]
    assert store.read(run["run_id"])["revision"] == 2


@pytest.mark.parametrize(
    "steps",
    [
        [],
        [{"label": "", "status": "active"}],
        [{"label": "A", "status": "active"}, {"label": "B", "status": "active"}],
        [{"label": "A", "status": "done"}],
        [{"label": "A", "status": "pending"}],
    ],
)
def test_invalid_start_does_not_create_a_run(
    store: ProgressStore, steps: list[dict[str, str]]
) -> None:
    with pytest.raises(ProgressError):
        store.start("开发任务", steps, "")


def test_bounded_history_and_private_data_directory(store: ProgressStore) -> None:
    run = store.start("开发任务", initial_steps(), "")
    for revision in range(1, 30):
        run = store.update(
            run["run_id"], revision, "running", initial_steps(), str(revision)
        )
    assert len(run["history"]) == 20
    if __import__("os").name == "posix":
        assert store.directory.stat().st_mode & 0o077 == 0


def test_store_rejects_symlink_data_directory(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")
    with pytest.raises(ProgressError, match="unsafe_data_directory"):
        ProgressStore(link)


def test_retention_keeps_the_just_created_task_even_with_equal_timestamps(
    store: ProgressStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    from progress_panel import state

    monkeypatch.setattr(state, "MAX_RUNS", 2)
    same_time = state.timestamp()
    monkeypatch.setattr(state, "timestamp", lambda: same_time)
    identifiers = iter(
        [
            "ffffffff-ffff-4fff-8fff-ffffffffffff",
            "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
            "00000000-0000-4000-8000-000000000000",
        ]
    )
    monkeypatch.setattr(state.uuid, "uuid4", lambda: next(identifiers))
    store.start("任务一", initial_steps())
    store.start("任务二", initial_steps())
    newest = store.start("任务三", initial_steps())
    assert store.read(newest["run_id"]) == newest
    with store.connection() as connection:
        assert connection.execute("SELECT count(*) FROM runs").fetchone()[0] == 2


def test_old_state_is_pruned_on_a_new_declaration(store: ProgressStore) -> None:
    old = store.start("旧任务", initial_steps())
    with store.connection() as connection:
        connection.execute(
            "UPDATE runs SET updated = ? WHERE id = ?",
            ("2000-01-01T00:00:00.000Z", old["run_id"]),
        )
    store.start("新任务", initial_steps())
    with pytest.raises(ProgressError, match="unknown_run"):
        store.read(old["run_id"])
