"""Run the simulated daily scheduler with example users and tasks."""

import argparse
import logging
from datetime import datetime

from strategy_scheduler import QuotaManager, Scheduler, Task, TaskExecutor


def parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected YYYY-MM-DDTHH:MM") from error
    if parsed.tzinfo is not None or parsed.strftime("%Y-%m-%dT%H:%M") != value:
        raise argparse.ArgumentTypeError("expected local YYYY-MM-DDTHH:MM")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="Run simulated tasks due at a local time")
    parser.add_argument("time", nargs="?", type=parse_time, default=datetime.now())
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    scheduler = Scheduler(QuotaManager({"alice": 3, "bob": 5}), TaskExecutor())
    tasks = [
        {"id": "sync-x", "user": "alice", "time": "12:00", "action": "sync", "target": "/data/x"},
        {"id": "backup-y", "user": "bob", "time": "12:00", "action": "backup", "target": "/srv/y"},
        {
            "id": "delete-z", "user": "alice", "time": "12:00",
            "action": "delete", "target": "/tmp/z",
        },
    ]
    for data in tasks:
        scheduler.add_task(Task.from_dict(data))
    for outcome in scheduler.run_due(args.time):
        logging.info("Outcome: task_id=%s status=%s", outcome.task_id, outcome.status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
