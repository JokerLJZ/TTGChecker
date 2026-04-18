from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass
class CheckinRecord:
    run_at: str
    success: bool
    message: str
    missed_dates: list[str] = field(default_factory=list)


class StateStore:
    def __init__(self, state_file: str | Path) -> None:
        self.path = Path(state_file).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"history": {}, "last_success_date": None, "last_run_at": None}
        with self.path.open("r", encoding="utf-8") as fp:
            return json.load(fp)

    def save(self, payload: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fp:
            json.dump(payload, fp, ensure_ascii=False, indent=2)
        tmp.replace(self.path)

    def already_checked_in_today(self, today: date | None = None) -> bool:
        current = today or date.today()
        return (
            self.load()
            .get("history", {})
            .get(current.isoformat(), {})
            .get("success", False)
        )

    def get_missed_dates(self, today: date | None = None, lookback_days: int = 7) -> list[str]:
        current = today or date.today()
        history = self.load().get("history", {})
        missed: list[str] = []
        for delta in range(lookback_days, 0, -1):
            d = (current - timedelta(days=delta)).isoformat()
            if not history.get(d, {}).get("success", False):
                missed.append(d)
        return missed

    def record(self, for_date: date, record: CheckinRecord) -> None:
        payload = self.load()
        history = payload.setdefault("history", {})
        history[for_date.isoformat()] = {
            "run_at": record.run_at,
            "success": record.success,
            "message": record.message,
            "missed_dates": record.missed_dates,
        }
        payload["last_run_at"] = record.run_at
        if record.success:
            payload["last_success_date"] = for_date.isoformat()
        self.save(payload)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
