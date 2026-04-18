from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date

from ttg_checker.client import (
    AlreadySignedError,
    CheckinError,
    NotLoggedInError,
    TtgClient,
)
from ttg_checker.config import AppConfig
from ttg_checker.notifier import WxPusherNotifier
from ttg_checker.state import CheckinRecord, StateStore, now_iso

LOGGER = logging.getLogger(__name__)


@dataclass
class RunSummary:
    success: bool
    message: str


class CheckinService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.state = StateStore(config.log.state_file)
        self.client = TtgClient(config.ttg)
        self.notifier = WxPusherNotifier(config.wxpusher)

    def execute(self) -> RunSummary:
        today = date.today()
        if self.state.already_checked_in_today(today):
            msg = "今日已签到（本地状态），跳过执行。"
            LOGGER.info(msg)
            return RunSummary(success=True, message=msg)

        missed = self.state.get_missed_dates(today)
        last_error: Exception | None = None

        for attempt in range(1, self.config.retry.max_attempts + 1):
            LOGGER.info("attempt %s/%s", attempt, self.config.retry.max_attempts)
            try:
                result = self.client.run_checkin()
                msg = self._build_success_msg(result.message, missed)
                self.state.record(
                    today,
                    CheckinRecord(run_at=now_iso(), success=True, message=msg, missed_dates=missed),
                )
                self.notifier.send("TTG 签到成功", msg)
                return RunSummary(success=True, message=msg)
            except AlreadySignedError as exc:
                msg = f"今日已签到（站点反馈）。{exc}"
                self.state.record(
                    today,
                    CheckinRecord(run_at=now_iso(), success=True, message=msg, missed_dates=missed),
                )
                self.notifier.send("TTG 已签到", msg)
                return RunSummary(success=True, message=msg)
            except NotLoggedInError as exc:
                msg = f"Cookie 失效，请重新从浏览器复制 Cookie 头。详情: {exc}"
                self.state.record(
                    today,
                    CheckinRecord(run_at=now_iso(), success=False, message=msg, missed_dates=missed),
                )
                self.notifier.send("TTG Cookie 失效", msg)
                return RunSummary(success=False, message=msg)
            except CheckinError as exc:
                last_error = exc
                LOGGER.warning("attempt %s failed: %s", attempt, exc)
                if attempt < self.config.retry.max_attempts:
                    time.sleep(self.config.retry.retry_interval_seconds)

        msg = self._build_failure_msg(str(last_error), missed)
        self.state.record(
            today,
            CheckinRecord(run_at=now_iso(), success=False, message=msg, missed_dates=missed),
        )
        self.notifier.send("TTG 签到失败", msg)
        return RunSummary(success=False, message=msg)

    @staticmethod
    def _build_success_msg(detail: str, missed: list[str]) -> str:
        if missed:
            return f"签到成功。最近 7 天漏签: {', '.join(missed)}。站点反馈: {detail}"
        return f"签到成功。站点反馈: {detail}"

    @staticmethod
    def _build_failure_msg(error: str, missed: list[str]) -> str:
        if missed:
            return f"签到失败。最近 7 天漏签: {', '.join(missed)}。错误: {error}"
        return f"签到失败。错误: {error}"
