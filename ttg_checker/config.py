from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TtgConfig:
    base_url: str
    cookie: str
    user_agent: str
    impersonate: str = "edge99"
    request_timeout_seconds: int = 30
    proxy: str | None = None


@dataclass
class RetryConfig:
    max_attempts: int = 3
    retry_interval_seconds: int = 30


@dataclass
class LogConfig:
    state_file: str = "data/checkin_log.json"


@dataclass
class WxPusherConfig:
    app_token: str
    uid: str
    topic_ids: list[int] = field(default_factory=list)
    base_url: str = "https://wxpusher.zjiecode.com/api/send/message"


@dataclass
class AppConfig:
    ttg: TtgConfig
    retry: RetryConfig
    log: LogConfig
    wxpusher: WxPusherConfig


def load_config(config_path: str | Path) -> AppConfig:
    path = Path(config_path).expanduser().resolve()
    with path.open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    return AppConfig(
        ttg=_build_ttg(raw.get("ttg", {})),
        retry=_build_retry(raw.get("retry", {})),
        log=_build_log(raw.get("log", {})),
        wxpusher=_build_wxpusher(raw.get("wxpusher", {})),
    )


def _build_ttg(data: dict[str, Any]) -> TtgConfig:
    cookie = str(data.get("cookie", "")).strip()
    if not cookie or cookie.startswith("PASTE_"):
        raise ValueError("ttg.cookie is required (paste full Cookie header from your browser)")
    user_agent = str(data.get("user_agent", "")).strip()
    if not user_agent:
        raise ValueError("ttg.user_agent is required and must match the browser used to obtain the cookie")
    proxy_raw = data.get("proxy")
    proxy = str(proxy_raw).strip() if proxy_raw else None
    return TtgConfig(
        base_url=str(data.get("base_url", "https://totheglory.im")).rstrip("/"),
        cookie=cookie,
        user_agent=user_agent,
        impersonate=str(data.get("impersonate", "edge99")),
        request_timeout_seconds=int(data.get("request_timeout_seconds", 30)),
        proxy=proxy or None,
    )


def _build_retry(data: dict[str, Any]) -> RetryConfig:
    return RetryConfig(
        max_attempts=int(data.get("max_attempts", 3)),
        retry_interval_seconds=int(data.get("retry_interval_seconds", 30)),
    )


def _build_log(data: dict[str, Any]) -> LogConfig:
    return LogConfig(state_file=str(data.get("state_file", "data/checkin_log.json")))


def _build_wxpusher(data: dict[str, Any]) -> WxPusherConfig:
    app_token = str(data.get("app_token", "")).strip()
    uid = str(data.get("uid", "")).strip()
    if not app_token or not uid or app_token.startswith("AT_xxxx"):
        raise ValueError("wxpusher.app_token and wxpusher.uid are required")
    return WxPusherConfig(
        app_token=app_token,
        uid=uid,
        topic_ids=[int(x) for x in data.get("topic_ids", [])],
        base_url=str(data.get("base_url", "https://wxpusher.zjiecode.com/api/send/message")),
    )
