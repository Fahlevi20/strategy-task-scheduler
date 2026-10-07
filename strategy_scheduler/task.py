"""Validated daily task definitions."""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, time


@dataclass(frozen=True)
class Task:
    id: str
    user: str
    time: str
    action: str
    target: str
    parameters: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("id", "user", "action", "target"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonblank string")
        if not isinstance(self.time, str) or not re.fullmatch(r"[0-2][0-9]:[0-5][0-9]", self.time):
            raise ValueError("time must use HH:MM")
        try:
            datetime.strptime(self.time, "%H:%M")
        except ValueError as error:
            raise ValueError("time must be a valid HH:MM") from error
        if not isinstance(self.parameters, Mapping):
            raise TypeError("parameters must be a dictionary")
        if any(not isinstance(key, str) or not key.strip() for key in self.parameters):
            raise ValueError("parameter keys must be nonblank strings")
        object.__setattr__(self, "parameters", dict(self.parameters))

    @property
    def scheduled_time(self) -> time:
        return datetime.strptime(self.time, "%H:%M").time()

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "Task":
        required = ("id", "user", "time", "action", "target")
        for name in required:
            if name not in data:
                raise ValueError(f"missing task field: {name}")
        return cls(*(data[name] for name in required), parameters=data.get("parameters", {}))
