# Strategy Task Scheduler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a runnable, tested Python daily task scheduler with per-user quotas counting successful executions only, logging, and CI checks.

**Architecture:** A small synchronous in-memory package separates task parsing, quota accounting, action dispatch, and scheduling. The example CLI passes a time explicitly; no real file operation occurs. The scheduler reports per-task outcomes and isolates handler failures.

**Tech Stack:** Python 3.11+ standard library (`dataclasses`, `datetime`, `logging`, `unittest`, `argparse`); Ruff for linting; GitHub Actions for CI.

**Spec:** `docs/superpowers/specs/2026-10-07-strategy-task-scheduler-design.md`

## Global Constraints

- Synchronous and in-memory; no database, network API, persistence, queue, or real filesystem actions.
- Daily quota is per username and supplied calendar date; count successes only.
- A task successfully run on a date must not run again that day. Failed tasks can retry when due.
- Accept naive local datetimes; document timezone and concurrency limits.
- Add `.gitignore`; no `.env.example` because no environment variables or credentials are required.
- Stop after local lint, tests, and example run and ask the user to test before any push. Never claim CI passed without observing the actual CI run.
- Work on `main` only for this new empty repository; the design was committed as `2181000`. Do not push without explicit approval after user testing.

## Review Focus

- Duplicate task IDs in registration: reject rather than silently corrupt completion bookkeeping (Task 4 test).
- A zero-quota user: every due task reports quota exceeded, never dispatches (Task 4 test).
- Blank or non-string task parameters: reject at input parsing rather than failing inside a handler (Task 1 test).
- A handler failing among multiple due tasks: report failure and continue processing later tasks (Task 4 test).
- A success at 23:59 followed by the same task at 00:00: date keys reset quota and completion (Task 4 test via a task scheduled at a fixed same minute on two days).

---

## File map

- `strategy_scheduler/__init__.py`: public exports of task, quota, executor, scheduler types.
- `strategy_scheduler/task.py`: immutable validated task data and dictionary parsing.
- `strategy_scheduler/quota.py`: in-memory per-user per-date successful-use counters.
- `strategy_scheduler/executor.py`: safe simulated action registry and logging.
- `strategy_scheduler/scheduler.py`: due filtering, quota gate, completion records, outcomes.
- `strategy_scheduler/__main__.py`: runnable example with optional ISO local datetime.
- `tests/test_task.py`, `tests/test_quota.py`, `tests/test_executor.py`, `tests/test_scheduler.py`: standard-library unit tests.
- `README.md`, `.gitignore`, `pyproject.toml`, `.github/workflows/ci.yml`: usage, ignored files, Ruff configuration, CI.

### Task 1: Validated task definitions

**Files:**
- Create: `strategy_scheduler/task.py`, `strategy_scheduler/__init__.py`, `tests/test_task.py`

**Interfaces:**
- Produces: `Task(id: str, user: str, time: str, action: str, target: str, parameters: dict[str, object])`; `Task.from_dict(data: Mapping[str, object]) -> Task`. `Task.scheduled_time` returns `datetime.time`. Validate `HH:MM` exactly and nonblank string fields. Copy parameters on input to avoid caller mutations.

- [ ] **Step 1: Write failing tests** in `tests/test_task.py` using `unittest.TestCase`:

```python
from unittest import TestCase
from strategy_scheduler.task import Task

class TaskTests(TestCase):
    def test_parse_parameters_and_time(self):
        raw = {"id": "t1", "user": "alice", "time": "12:00", "action": "sync", "target": "/data/x", "parameters": {"priority": 2}}
        task = Task.from_dict(raw)
        raw["parameters"]["priority"] = 9
        self.assertEqual(task.parameters, {"priority": 2})
        self.assertEqual(task.scheduled_time.isoformat(timespec="minutes"), "12:00")

    def test_invalid_inputs(self):
        base = {"id": "t1", "user": "alice", "time": "12:00", "action": "sync", "target": "/data/x"}
        for change in ({"time": "12:00:01"}, {"time": "25:00"}, {"user": " "}, {"parameters": "bad"}, {"parameters": {" ": 1}}):
            with self.subTest(change=change), self.assertRaises((TypeError, ValueError)):
                Task.from_dict({**base, **change})
```

- [ ] **Step 2: Verify red**: `python -m unittest discover -s tests -p 'test_task.py' -v` must fail from missing module.
- [ ] **Step 3: Implement** `@dataclass(frozen=True)` task; `__post_init__` validates required strings, `re.fullmatch(r"[0-2][0-9]:[0-5][0-9]", ...)` plus `datetime.strptime`, and copies a validated string-keyed parameters mapping. `from_dict` reads required keys and defaults parameters to `{}`; missing keys yield `ValueError` naming the field. Expose task in `__init__.py`.
- [ ] **Step 4: Verify green**: run the same test command; both tests pass.
- [ ] **Step 5: Commit**: `git add strategy_scheduler tests/test_task.py && git commit -m "feat: validate scheduled task definitions" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"`.

### Task 2: Daily user quotas

**Files:**
- Create: `strategy_scheduler/quota.py`, `tests/test_quota.py`
- Modify: `strategy_scheduler/__init__.py`

**Interfaces:**
- Produces: `QuotaManager(quotas: Mapping[str, int])`; `can_run(user: str, day: date) -> bool`; `record_success(user: str, day: date) -> None`; `executed(user: str, day: date) -> int`. Reject unknown users with `ValueError`; validate nonnegative integer quota, excluding bool. Single-process only.

- [ ] **Step 1: Write failing tests** in `tests/test_quota.py`:

```python
from datetime import date
from unittest import TestCase
from strategy_scheduler.quota import QuotaManager

class QuotaTests(TestCase):
    def test_daily_success_counts(self):
        quota = QuotaManager({"alice": 1, "bob": 0})
        today, tomorrow = date(2026, 10, 7), date(2026, 10, 8)
        self.assertTrue(quota.can_run("alice", today))
        quota.record_success("alice", today)
        self.assertFalse(quota.can_run("alice", today))
        self.assertTrue(quota.can_run("alice", tomorrow))
        self.assertFalse(quota.can_run("bob", today))
        self.assertEqual(quota.executed("alice", today), 1)

    def test_invalid_users_and_quota(self):
        with self.assertRaises(ValueError):
            QuotaManager({"alice": True})
        quota = QuotaManager({"alice": 1})
        with self.assertRaises(ValueError):
            quota.can_run("nobody", date.today())
        quota.record_success("alice", date.today())
        with self.assertRaises(ValueError):
            quota.record_success("alice", date.today())
```

- [ ] **Step 2: Verify red**: `python -m unittest discover -s tests -p 'test_quota.py' -v` fails from missing module.
- [ ] **Step 3: Implement** dictionary keyed `(username, date)`; `record_success` checks `can_run` before incrementing; validate quotas and names in constructor; export from package.
- [ ] **Step 4: Verify green**: same test command passes.
- [ ] **Step 5: Commit**: `git add strategy_scheduler tests/test_quota.py && git commit -m "feat: track daily successful quotas" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"`.

### Task 3: Extensible simulated action execution

**Files:**
- Create: `strategy_scheduler/executor.py`, `tests/test_executor.py`
- Modify: `strategy_scheduler/__init__.py`

**Interfaces:**
- Consumes: `Task` from Task 1.
- Produces: `TaskExecutor(actions: Mapping[str, Callable[[Task], object]] | None = None, logger: logging.Logger | None = None)`; `has_action(name: str) -> bool`; `execute(task: Task) -> object`. Default registry has `sync`, `backup`, `delete` simulated no-op handlers; custom mapping extends/overrides defaults. Invalid names raise `ValueError`; handler exceptions propagate after `logger.exception` (scheduler catches them). Success logged using `logger.info`.

- [ ] **Step 1: Write failing tests** in `tests/test_executor.py`:

```python
from unittest import TestCase
from strategy_scheduler.executor import TaskExecutor
from strategy_scheduler.task import Task

class ExecutorTests(TestCase):
    def test_custom_handler_receives_parameters(self):
        seen = []
        executor = TaskExecutor(actions={"inspect": lambda task: seen.append(task.parameters["depth"])})
        task = Task("t1", "alice", "12:00", "inspect", "/data", {"depth": 2})
        executor.execute(task)
        self.assertEqual(seen, [2])

    def test_defaults_are_safe_and_unknown_action_rejected(self):
        executor = TaskExecutor()
        task = Task("t2", "alice", "12:00", "delete", "/do/not/delete", {})
        executor.execute(task)
        self.assertFalse(executor.has_action("unknown"))
        with self.assertRaises(ValueError):
            executor.execute(Task("t3", "alice", "12:00", "unknown", "/data", {}))
```

- [ ] **Step 2: Verify red**: `python -m unittest discover -s tests -p 'test_executor.py' -v` fails from missing module.
- [ ] **Step 3: Implement** default safe handlers (no filesystem calls), registry merging, action lookup, contextual success and exception logging. Keep unknown action validation at scheduler registration for submitted tasks, and `execute` validates independently for direct use.
- [ ] **Step 4: Verify green**: same test command passes.
- [ ] **Step 5: Commit**: `git add strategy_scheduler tests/test_executor.py && git commit -m "feat: dispatch simulated task actions" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"`.

### Task 4: Scheduling and observable outcomes

**Files:**
- Create: `strategy_scheduler/scheduler.py`, `tests/test_scheduler.py`
- Modify: `strategy_scheduler/__init__.py`

**Interfaces:**
- Consumes: `Task`, `QuotaManager`, `TaskExecutor` interfaces above.
- Produces: `Scheduler(quota: QuotaManager, executor: TaskExecutor, logger: logging.Logger | None = None)`; `add_task(task: Task) -> None` (reject duplicate ID and unknown action/user); `run_due(now: datetime) -> list[TaskOutcome]`, where immutable `TaskOutcome(task_id: str, status: Literal["success", "already_completed", "quota_exceeded", "failed"], error: str | None = None)`. Only due tasks have outcomes. Catch handler exceptions, not arbitrary scheduler programming errors; failed task remains retryable. All state held in memory.

- [ ] **Step 1: Write failing tests** in `tests/test_scheduler.py`:

```python
from datetime import datetime, timedelta
from unittest import TestCase
from strategy_scheduler import QuotaManager, Task, TaskExecutor, Scheduler

class SchedulerTests(TestCase):
    def test_due_multiple_quota_and_reset(self):
        now = datetime(2026, 10, 7, 12, 0)
        scheduler = Scheduler(QuotaManager({"alice": 2, "bob": 0}), TaskExecutor())
        for task_id in ("one", "two", "three"):
            scheduler.add_task(Task(task_id, "alice", "12:00", "sync", "/data", {}))
        scheduler.add_task(Task("bob", "bob", "12:00", "backup", "/data", {}))
        scheduler.add_task(Task("later", "alice", "12:01", "sync", "/data", {}))
        self.assertEqual([r.status for r in scheduler.run_due(now)], ["success", "success", "quota_exceeded", "quota_exceeded"])
        self.assertEqual([r.status for r in scheduler.run_due(now)], ["already_completed", "already_completed", "quota_exceeded", "quota_exceeded"])
        self.assertEqual([r.status for r in scheduler.run_due(now + timedelta(days=1))], ["success", "success", "quota_exceeded", "quota_exceeded"])

    def test_failure_does_not_consume_quota_and_does_not_block_next_task(self):
        calls = []
        def fail(task):
            raise RuntimeError("broken")
        scheduler = Scheduler(QuotaManager({"alice": 1}), TaskExecutor(actions={"fail": fail, "ok": lambda task: calls.append(task.id)}))
        scheduler.add_task(Task("bad", "alice", "12:00", "fail", "/data", {}))
        scheduler.add_task(Task("good", "alice", "12:00", "ok", "/data", {}))
        self.assertEqual([r.status for r in scheduler.run_due(datetime(2026, 10, 7, 12))], ["failed", "success"])
        self.assertEqual(calls, ["good"])

    def test_reject_duplicate_unknown_user_and_unknown_action(self):
        scheduler = Scheduler(QuotaManager({"alice": 1}), TaskExecutor())
        task = Task("one", "alice", "12:00", "sync", "/data", {})
        scheduler.add_task(task)
        for bad in (task, Task("two", "nobody", "12:00", "sync", "/data", {}), Task("three", "alice", "12:00", "missing", "/data", {})):
            with self.assertRaises(ValueError):
                scheduler.add_task(bad)
```

- [ ] **Step 2: Verify red**: `python -m unittest discover -s tests -p 'test_scheduler.py' -v` fails from missing scheduler.
- [ ] **Step 3: Implement** registration validation, list preserving insertion order, `set[tuple[str, date]]` completion records, and ordered per-task outcomes. Compare `now.strftime('%H:%M')` to the task time. Check completion before quota. On success record quota before marking completion; log quota skips and handler failures (executor logs stack trace). Do not catch unknown users during due processing because registration already checks them.
- [ ] **Step 4: Verify green**: same test command and `python -m unittest discover -s tests -v` pass.
- [ ] **Step 5: Commit**: `git add strategy_scheduler tests/test_scheduler.py && git commit -m "feat: schedule daily tasks with quota and deduplication" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"`.

### Task 5: Runnable demonstration, lint, CI, and documentation

**Files:**
- Create: `strategy_scheduler/__main__.py`, `README.md`, `.gitignore`, `pyproject.toml`, `.github/workflows/ci.yml`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `Scheduler`, `QuotaManager`, `TaskExecutor`, `Task.from_dict`.
- Produces: `python -m strategy_scheduler [YYYY-MM-DDTHH:MM]` exits 0 and logs sample execution; malformed time exits nonzero via `argparse`.

- [ ] **Step 1: Write failing CLI test** in `tests/test_cli.py`:

```python
import subprocess
import sys
from unittest import TestCase

class CliTests(TestCase):
    def test_example_runs(self):
        result = subprocess.run([sys.executable, "-m", "strategy_scheduler", "2026-10-07T12:00"], capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("alice", result.stderr)

    def test_bad_time_is_rejected(self):
        result = subprocess.run([sys.executable, "-m", "strategy_scheduler", "not-a-time"], capture_output=True, text=True, check=False)
        self.assertNotEqual(result.returncode, 0)
```

- [ ] **Step 2: Verify red**: `python -m unittest discover -s tests -p 'test_cli.py' -v` fails because no `__main__` exists.
- [ ] **Step 3: Implement CLI** using `argparse`, `datetime.fromisoformat` with strict minute format (parse and compare roundtrip), configure `logging.basicConfig(level=logging.INFO)`, create sample users and task dictionaries from `context.md` with IDs, call scheduler, and return 0. Write README with setup, `python -m unittest discover -s tests -v`, `python -m strategy_scheduler 2026-10-07T12:00`, `ruff check .`, behavior and limitations, CI, and AI-assistance explanation. `.gitignore`: `__pycache__/`, `*.py[cod]`, `.venv/`, `.env`, `.env.*`, `!.env.example`, `.ruff_cache/`, `.pytest_cache/`, `.coverage`, `htmlcov/`. `pyproject.toml` sets Ruff `target-version = "py311"`, `line-length = 100`, `lint.select = ["E", "F", "I", "B"]`. CI on `push` and `pull_request`: Python 3.11 setup, `python -m pip install ruff`, `ruff check .`, `python -m unittest discover -s tests -v`. No credentials are used and no `.env.example` is needed.
- [ ] **Step 4: Verify green locally**: install Ruff if unavailable (`python -m pip install ruff`); run `python -m unittest discover -s tests -v`, `ruff check .`, and `python -m strategy_scheduler 2026-10-07T12:00`. Resolve any failures; record command outputs for user. Check `git status --short` so no secrets/artifacts are staged.
- [ ] **Step 5: Commit**: `git add .gitignore README.md pyproject.toml .github/workflows/ci.yml strategy_scheduler/__main__.py tests/test_cli.py && git commit -m "chore: add runnable example lint and CI" -m "Co-Authored-By: Claude Code <noreply@anthropic.com>"`.
- [ ] **Step 6: Pause for user testing**: communicate commands and results, ask the user to test and review. Only after explicit approval push (`git push -u origin main`) and inspect GitHub Actions status via `gh run list` / `gh run view` if authenticated; accurately report CI status and fix any failures.
