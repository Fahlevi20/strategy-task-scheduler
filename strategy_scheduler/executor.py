"""Safe in-memory simulated action dispatch."""

import logging
from collections.abc import Callable, Mapping

from strategy_scheduler.task import Task


def _simulate(task: Task) -> None:
    """Default actions intentionally do not touch their target."""


class TaskExecutor:
    def __init__(
        self,
        actions: Mapping[str, Callable[[Task], object]] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._actions: dict[str, Callable[[Task], object]] = {
            "sync": _simulate,
            "backup": _simulate,
            "delete": _simulate,
        }
        if actions is not None:
            self._actions.update(actions)
        self._logger = logger or logging.getLogger(__name__)

    def has_action(self, name: str) -> bool:
        return name in self._actions

    def execute(self, task: Task) -> object:
        if not self.has_action(task.action):
            raise ValueError(f"unknown action: {task.action}")
        try:
            result = self._actions[task.action](task)
        except Exception:
            self._logger.exception(
                "Task failed: id=%s user=%s action=%s", task.id, task.user, task.action
            )
            raise
        self._logger.info(
            "Task succeeded: id=%s user=%s action=%s target=%s",
            task.id, task.user, task.action, task.target,
        )
        return result
