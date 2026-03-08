from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date

from ttg_checker.browser import CheckinError, TtgBrowserClient
from ttg_checker.config import AppConfig
from ttg_checker.notifier import WxPusherNotifier
from ttg_checker.state import CheckinRecord, StateStore, now_iso


@dataclass(slots=True)
class RunSummary:
    success: bool
    message: str
    screenshot: str | None


class CheckinService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.state = StateStore(config.log.state_file)
        self.browser = TtgBrowserClient(config.browser, config.ttg)
        self.notifier = WxPusherNotifier(config.wxpusher)

    def execute(self) -> RunSummary:
        today = date.today()
        missed_dates = self.state.get_missed_dates(today=today)
        if self.state.already_checked_in_today(today=today):
            message = "今日已记录为签到成功，跳过重复执行。"
            self.notifier.send("TTG 已签到", message)
            return RunSummary(success=True, message=message, screenshot=None)

        last_error: CheckinError | None = None
        for attempt in range(1, self.config.retry.max_attempts + 1):
            try:
                result = self.browser.run_checkin()
                notice = self._build_success_message(result.message, missed_dates)
                self.state.record(
                    today,
                    CheckinRecord(
                        run_at=now_iso(),
                        success=True,
                        message=notice,
                        screenshot=result.screenshot_path,
                        missed_dates=missed_dates,
                    ),
                )
                self.notifier.send("TTG 签到成功", notice)
                return RunSummary(
                    success=True,
                    message=notice,
                    screenshot=result.screenshot_path,
                )
            except CheckinError as exc:
                last_error = exc
                if attempt < self.config.retry.max_attempts:
                    time.sleep(self.config.retry.retry_interval_seconds)

        assert last_error is not None
        failure_message = self._build_failure_message(str(last_error), missed_dates)
        screenshot = self._extract_screenshot_path(str(last_error))
        self.state.record(
            today,
            CheckinRecord(
                run_at=now_iso(),
                success=False,
                message=failure_message,
                screenshot=screenshot,
                missed_dates=missed_dates,
            ),
        )
        self.notifier.send("TTG 签到异常", failure_message)
        return RunSummary(success=False, message=failure_message, screenshot=screenshot)

    @staticmethod
    def _extract_screenshot_path(message: str) -> str | None:
        marker = "screenshot="
        if marker not in message:
            return None
        return message.split(marker, maxsplit=1)[1].strip()

    @staticmethod
    def _build_success_message(page_message: str, missed_dates: list[str]) -> str:
        if missed_dates:
            return f"签到执行成功。检测到待补救日期: {', '.join(missed_dates)}。站点不支持历史补签，已对当前日期执行即时重试。页面反馈: {page_message}"
        return f"签到执行成功。页面反馈: {page_message}"

    @staticmethod
    def _build_failure_message(error: str, missed_dates: list[str]) -> str:
        if missed_dates:
            return f"签到失败。检测到漏签日期: {', '.join(missed_dates)}。错误信息: {error}"
        return f"签到失败。错误信息: {error}"
