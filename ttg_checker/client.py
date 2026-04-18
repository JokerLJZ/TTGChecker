from __future__ import annotations

import logging
import random
import re
import time
from dataclasses import dataclass

from curl_cffi import requests as cffi_requests

from ttg_checker.config import TtgConfig

LOGGER = logging.getLogger(__name__)


class CheckinError(RuntimeError):
    """Raised when check-in cannot be completed."""


class AlreadySignedError(CheckinError):
    """Raised when the homepage shows the account has already signed in today."""


class NotLoggedInError(CheckinError):
    """Raised when the cookie is invalid or expired."""


@dataclass
class CheckinResult:
    success: bool
    message: str
    raw_response: str


# Inline jQuery payload set by PHP, e.g.:
#   $.post("signed.php", {signed_timestamp: "1700000000", signed_token: "abc...32hex..."}, ...)
_TIMESTAMP_RE = re.compile(r"""signed_timestamp\s*:\s*['"](\d{10})['"]""")
_TOKEN_RE = re.compile(r"""signed_token\s*:\s*['"]([a-fA-F0-9]{32})['"]""")
# Logged-in pages always render the username link in the top bar.
_LOGGED_OUT_MARKERS = ("login.php", "用户名", "Username")


class TtgClient:
    def __init__(self, config: TtgConfig) -> None:
        self.config = config
        self._session = cffi_requests.Session(impersonate=config.impersonate)
        self._session.headers.update(self._base_headers())
        if config.proxy:
            self._session.proxies = {"http": config.proxy, "https": config.proxy}

    def _base_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.config.user_agent,
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cookie": self.config.cookie,
        }

    def fetch_home(self) -> str:
        url = self.config.base_url + "/"
        LOGGER.info("GET %s", url)
        resp = self._session.get(
            url,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            },
            timeout=self.config.request_timeout_seconds,
        )
        if resp.status_code != 200:
            raise CheckinError(f"home page returned HTTP {resp.status_code}")
        text = resp.text
        if any(marker in text for marker in _LOGGED_OUT_MARKERS) and "logout.php" not in text:
            raise NotLoggedInError("cookie is invalid or expired (login form detected)")
        return text

    def parse_signed_params(self, home_html: str) -> tuple[str, str] | None:
        ts = _TIMESTAMP_RE.search(home_html)
        tok = _TOKEN_RE.search(home_html)
        if not ts or not tok:
            return None
        return ts.group(1), tok.group(1)

    def post_signed(self, timestamp: str, token: str) -> str:
        url = self.config.base_url + "/signed.php"
        LOGGER.info("POST %s", url)
        # 1-3s human-like delay between page load and click
        time.sleep(random.uniform(1.2, 3.4))
        resp = self._session.post(
            url,
            data={"signed_timestamp": timestamp, "signed_token": token},
            headers={
                "Accept": "*/*",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Origin": self.config.base_url,
                "Referer": self.config.base_url + "/",
                "X-Requested-With": "XMLHttpRequest",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
            },
            timeout=self.config.request_timeout_seconds,
        )
        if resp.status_code != 200:
            raise CheckinError(f"signed.php returned HTTP {resp.status_code}: {resp.text[:200]}")
        return resp.text

    def run_checkin(self) -> CheckinResult:
        home = self.fetch_home()
        params = self.parse_signed_params(home)
        if params is None:
            # No params = either already signed today, or page layout changed.
            if any(kw in home for kw in ("已签到", "已簽到", "今日已签", "签到成功")):
                raise AlreadySignedError("homepage indicates already signed today")
            raise CheckinError("cannot find signed_timestamp/signed_token in homepage (layout changed?)")
        timestamp, token = params
        body = self.post_signed(timestamp, token)
        message = self._summarize_response(body)
        success = self._is_success(body)
        if not success:
            raise CheckinError(f"signed.php response did not indicate success: {message}")
        return CheckinResult(success=True, message=message, raw_response=body)

    @staticmethod
    def _is_success(body: str) -> bool:
        text = body.strip()
        if not text:
            return False
        # Explicit failure signals (anti-bot / cheat detection)
        bad = ("作弊", "脚本", "bot", "异常", "请勿", "失败")
        if any(b in text for b in bad):
            return False
        good = ("成功", "已签到", "已簽到", "magic", "魔力", "积分", "獎勵", "奖励", "+")
        return any(g in text for g in good)

    @staticmethod
    def _summarize_response(body: str) -> str:
        cleaned = re.sub(r"<[^>]+>", " ", body)
        cleaned = " ".join(cleaned.split())
        return cleaned[:500]
