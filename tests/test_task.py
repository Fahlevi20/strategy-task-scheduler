from unittest import TestCase

from strategy_scheduler.task import Task


class TaskTests(TestCase):
    def test_parse_parameters_and_time(self):
        raw = {
            "id": "t1", "user": "alice", "time": "12:00", "action": "sync",
            "target": "/data/x", "parameters": {"priority": 2},
        }
        task = Task.from_dict(raw)
        raw["parameters"]["priority"] = 9
        self.assertEqual(task.parameters, {"priority": 2})
        self.assertEqual(task.scheduled_time.isoformat(timespec="minutes"), "12:00")

    def test_invalid_inputs(self):
        base = {"id": "t1", "user": "alice", "time": "12:00", "action": "sync", "target": "/data/x"}
        for change in (
            {"time": "12:00:01"}, {"time": "25:00"}, {"user": " "},
            {"parameters": "bad"}, {"parameters": {" ": 1}},
        ):
            with self.subTest(change=change), self.assertRaises((TypeError, ValueError)):
                Task.from_dict({**base, **change})
