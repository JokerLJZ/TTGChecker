from __future__ import annotations

import logging
from typing import Any

from curl_cffi import requests as cffi_requests

from ttg_checker.config import WxPusherConfig

LOGGER = logging.getLogger(__name__)


class WxPusherNotifier:
    def __init__(self, config: WxPusherConfig) -> None:
        self.config = config

    def send(self, summary: str, content: str) -> dict[str, Any] | None:
        payload = {
            "appToken": self.config.app_token,
            "content": content,
            "summary": summary[:20],
            "contentType": 1,
            "uids": [self.config.uid],
        }
        if self.config.topic_ids:
            payload["topicIds"] = self.config.topic_ids
        try:
            resp = cffi_requests.post(self.config.base_url, json=payload, timeout=20)
            data = resp.json()
        except Exception as exc:
            LOGGER.warning("WxPusher send failed: %s", exc)
            return None
        if data.get("code") != 1000:
            LOGGER.warning("WxPusher returned non-success: %s", data)
        return data
