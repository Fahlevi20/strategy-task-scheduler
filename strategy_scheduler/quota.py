"""Daily successful-execution quota accounting."""

from collections.abc import Mapping
from datetime import date


class QuotaManager:
    def __init__(self, quotas: Mapping[str, int]) -> None:
        for user, limit in quotas.items():
            if not isinstance(user, str) or not user.strip():
                raise ValueError("usernames must be nonblank strings")
            if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
                raise ValueError(f"quota for {user} must be a nonnegative integer")
        self._quotas = dict(quotas)
        self._executions: dict[tuple[str, date], int] = {}

    def executed(self, user: str, day: date) -> int:
        if user not in self._quotas:
            raise ValueError(f"unknown user: {user}")
        return self._executions.get((user, day), 0)

    def can_run(self, user: str, day: date) -> bool:
        return self.executed(user, day) < self._quotas[user]

    def record_success(self, user: str, day: date) -> None:
        if not self.can_run(user, day):
            raise ValueError(f"daily quota exceeded for {user}")
        key = (user, day)
        self._executions[key] = self.executed(user, day) + 1
