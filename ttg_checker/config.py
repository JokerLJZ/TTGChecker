from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class BrowserConfig:
    user_data_dir: str
    channel: str = "chrome"
    executable_path: str | None = None
    headless: bool = False
    slow_mo_ms: int = 0
    action_delay_seconds: tuple[float, float] = (1.0, 3.0)
    navigation_timeout_ms: int = 45_000
    screenshot_dir: str = "artifacts/screenshots"
    user_agent: str | None = None


@dataclass(slots=True)
class TtgConfig:
    base_url: str = "https://totheglory.im"
    checkin_url: str = "https://totheglory.im"
    success_keywords: list[str] = field(
        default_factory=lambda: ["签到成功", "magic", "魔力", "已签到", "获得"]
    )
    logged_out_keywords: list[str] = field(
        default_factory=lambda: ["login", "登录", "sign in", "用户名", "密码"]
    )
    button_selectors: list[str] = field(
        default_factory=lambda: [
            "text=签到",
            "text=簽到",
            "text=Check In",
            "a[href*='attendance']",
            "a[href*='checkin']",
            "button:has-text('签到')",
            "button:has-text('Check In')",
        ]
    )
    success_message_selectors: list[str] = field(
        default_factory=lambda: [
            ".alert",
            ".message",
            ".notice",
            ".success",
            "#info_block",
            "body",
        ]
    )


@dataclass(slots=True)
class RetryConfig:
    max_attempts: int = 2
    retry_interval_seconds: int = 10


@dataclass(slots=True)
class LogConfig:
    state_file: str = "data/checkin_log.json"


@dataclass(slots=True)
class WxPusherConfig:
    app_token: str
    uid: str
    topic_ids: list[int] = field(default_factory=list)
    base_url: str = "https://wxpusher.zjiecode.com/api/send/message"


@dataclass(slots=True)
class AppConfig:
    browser: BrowserConfig
    ttg: TtgConfig
    retry: RetryConfig
    log: LogConfig
    wxpusher: WxPusherConfig


def load_config(config_path: str | Path) -> AppConfig:
    path = Path(config_path).expanduser().resolve()
    with path.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    return AppConfig(
        browser=_build_browser_config(raw.get("browser", {})),
        ttg=_build_ttg_config(raw.get("ttg", {})),
        retry=_build_retry_config(raw.get("retry", {})),
        log=_build_log_config(raw.get("log", {})),
        wxpusher=_build_wxpusher_config(raw.get("wxpusher", {})),
    )


def _build_browser_config(data: dict[str, Any]) -> BrowserConfig:
    user_data_dir = str(data.get("user_data_dir", "")).strip()
    if not user_data_dir:
        raise ValueError("browser.user_data_dir is required")

    delay = data.get("action_delay_seconds", [1.0, 3.0])
    if not isinstance(delay, list) or len(delay) != 2:
        raise ValueError("browser.action_delay_seconds must be a list with two numbers")

    return BrowserConfig(
        user_data_dir=user_data_dir,
        channel=str(data.get("channel", "chrome")),
        executable_path=data.get("executable_path"),
        headless=bool(data.get("headless", False)),
        slow_mo_ms=int(data.get("slow_mo_ms", 0)),
        action_delay_seconds=(float(delay[0]), float(delay[1])),
        navigation_timeout_ms=int(data.get("navigation_timeout_ms", 45_000)),
        screenshot_dir=str(data.get("screenshot_dir", "artifacts/screenshots")),
        user_agent=data.get("user_agent"),
    )


def _build_ttg_config(data: dict[str, Any]) -> TtgConfig:
    return TtgConfig(
        base_url=str(data.get("base_url", "https://totheglory.im")),
        checkin_url=str(data.get("checkin_url", data.get("base_url", "https://totheglory.im"))),
        success_keywords=list(data.get("success_keywords", TtgConfig().success_keywords)),
        logged_out_keywords=list(data.get("logged_out_keywords", TtgConfig().logged_out_keywords)),
        button_selectors=list(data.get("button_selectors", TtgConfig().button_selectors)),
        success_message_selectors=list(
            data.get("success_message_selectors", TtgConfig().success_message_selectors)
        ),
    )


def _build_retry_config(data: dict[str, Any]) -> RetryConfig:
    return RetryConfig(
        max_attempts=int(data.get("max_attempts", 2)),
        retry_interval_seconds=int(data.get("retry_interval_seconds", 10)),
    )


def _build_log_config(data: dict[str, Any]) -> LogConfig:
    return LogConfig(state_file=str(data.get("state_file", "data/checkin_log.json")))


def _build_wxpusher_config(data: dict[str, Any]) -> WxPusherConfig:
    app_token = str(data.get("app_token", "")).strip()
    uid = str(data.get("uid", "")).strip()
    if not app_token or not uid:
        raise ValueError("wxpusher.app_token and wxpusher.uid are required")

    topic_ids = [int(item) for item in data.get("topic_ids", [])]
    return WxPusherConfig(
        app_token=app_token,
        uid=uid,
        topic_ids=topic_ids,
        base_url=str(data.get("base_url", "https://wxpusher.zjiecode.com/api/send/message")),
    )
