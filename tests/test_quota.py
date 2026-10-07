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
