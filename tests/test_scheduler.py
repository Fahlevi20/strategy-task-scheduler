from datetime import datetime, timedelta
from unittest import TestCase

from strategy_scheduler import QuotaManager, Scheduler, Task, TaskExecutor


class SchedulerTests(TestCase):
    def test_due_multiple_quota_and_reset(self):
        now = datetime(2026, 10, 7, 12, 0)
        scheduler = Scheduler(QuotaManager({"alice": 2, "bob": 0}), TaskExecutor())
        for task_id in ("one", "two", "three"):
            scheduler.add_task(Task(task_id, "alice", "12:00", "sync", "/data", {}))
        scheduler.add_task(Task("bob", "bob", "12:00", "backup", "/data", {}))
        scheduler.add_task(Task("later", "alice", "12:01", "sync", "/data", {}))
        expected = ["success", "success", "quota_exceeded", "quota_exceeded"]
        self.assertEqual([r.status for r in scheduler.run_due(now)], expected)
        self.assertEqual(
            [r.status for r in scheduler.run_due(now)],
            ["already_completed", "already_completed", "quota_exceeded", "quota_exceeded"],
        )
        self.assertEqual([r.status for r in scheduler.run_due(now + timedelta(days=1))], expected)

    def test_failure_does_not_consume_quota_and_does_not_block_next_task(self):
        calls = []

        def fail(task):
            raise RuntimeError("broken")

        scheduler = Scheduler(
            QuotaManager({"alice": 1}),
            TaskExecutor(actions={"fail": fail, "ok": lambda task: calls.append(task.id)}),
        )
        scheduler.add_task(Task("bad", "alice", "12:00", "fail", "/data", {}))
        scheduler.add_task(Task("good", "alice", "12:00", "ok", "/data", {}))
        self.assertEqual(
            [r.status for r in scheduler.run_due(datetime(2026, 10, 7, 12))],
            ["failed", "success"],
        )
        self.assertEqual(calls, ["good"])

    def test_reject_duplicate_unknown_user_and_unknown_action(self):
        scheduler = Scheduler(QuotaManager({"alice": 1}), TaskExecutor())
        task = Task("one", "alice", "12:00", "sync", "/data", {})
        scheduler.add_task(task)
        for bad in (
            task,
            Task("two", "nobody", "12:00", "sync", "/data", {}),
            Task("three", "alice", "12:00", "missing", "/data", {}),
        ):
            with self.assertRaises(ValueError):
                scheduler.add_task(bad)
