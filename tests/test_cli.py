import subprocess
import sys
from unittest import TestCase


class CliTests(TestCase):
    def test_example_runs(self):
        result = subprocess.run(
            [sys.executable, "-m", "strategy_scheduler", "2026-10-07T12:00"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("alice", result.stderr)

    def test_bad_time_is_rejected(self):
        result = subprocess.run(
            [sys.executable, "-m", "strategy_scheduler", "not-a-time"],
            capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
