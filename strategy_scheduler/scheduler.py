"""Daily scheduling and outcome reporting."""

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from strategy_scheduler.executor import TaskExecutor
from strategy_scheduler.quota import QuotaManager
from strategy_scheduler.task import Task


@dataclass(frozen=True)
class TaskOutcome:
    task_id: str
    status: Literal["success", "already_completed", "quota_exceeded", "failed"]
    error: str | None = None


class Scheduler:
    def __init__(
        self,
        quota: QuotaManager,
        executor: TaskExecutor,
        logger: logging.Logger | None = None,
    ) -> None:
        self._quota = quota
        self._executor = executor
        self._logger = logger or logging.getLogger(__name__)
        self._tasks: list[Task] = []
        self._ids: set[str] = set()
        self._completed: set[tuple[str, date]] = set()

    def add_task(self, task: Task) -> None:
        if task.id in self._ids:
            raise ValueError(f"duplicate task id: {task.id}")
        if not self._executor.has_action(task.action):
            raise ValueError(f"unknown action: {task.action}")
        self._quota.executed(task.user, date.today())
        self._tasks.append(
            Task(task.id, task.user, task.time, task.action, task.target, task.parameters)
        )
        self._ids.add(task.id)

    def run_due(self, now: datetime) -> list[TaskOutcome]:
        outcomes: list[TaskOutcome] = []
        for task in self._tasks:
            if task.time != now.strftime("%H:%M"):
                continue
            key = (task.id, now.date())
            if key in self._completed:
                outcomes.append(TaskOutcome(task.id, "already_completed"))
            elif not self._quota.can_run(task.user, now.date()):
                self._logger.warning("Quota exceeded: id=%s user=%s", task.id, task.user)
                outcomes.append(TaskOutcome(task.id, "quota_exceeded"))
            else:
                try:
                    self._executor.execute(task)
                except Exception as error:
                    outcomes.append(TaskOutcome(task.id, "failed", str(error)))
                else:
                    self._quota.record_success(task.user, now.date())
                    self._completed.add(key)
                    outcomes.append(TaskOutcome(task.id, "success"))
        return outcomes
