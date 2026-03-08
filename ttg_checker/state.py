from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class CheckinRecord:
    run_at: str
    success: bool
    message: str
    screenshot: str | None = None
    missed_dates: list[str] = field(default_factory=list)


class StateStore:
    def __init__(self, state_file: str | Path) -> None:
        self.path = Path(state_file).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"history": {}, "last_success_date": None, "last_run_at": None}
        with self.path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def save(self, payload: dict[str, Any]) -> None:
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)

    def get_missed_dates(self, today: date | None = None) -> list[str]:
        current_day = today or date.today()
        payload = self.load()
        history = payload.get("history", {})
        targets = [current_day - timedelta(days=1), current_day]
        return [
            item.isoformat()
            for item in targets
            if not history.get(item.isoformat(), {}).get("success", False)
        ]

    def already_checked_in_today(self, today: date | None = None) -> bool:
        current_day = today or date.today()
        payload = self.load()
        return payload.get("history", {}).get(current_day.isoformat(), {}).get("success", False)

    def record(self, for_date: date, record: CheckinRecord) -> None:
        payload = self.load()
        history = payload.setdefault("history", {})
        history[for_date.isoformat()] = {
            "run_at": record.run_at,
            "success": record.success,
            "message": record.message,
            "screenshot": record.screenshot,
            "missed_dates": record.missed_dates,
        }
        payload["last_run_at"] = record.run_at
        if record.success:
            payload["last_success_date"] = for_date.isoformat()
        self.save(payload)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
