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
