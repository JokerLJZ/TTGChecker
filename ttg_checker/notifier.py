from __future__ import annotations

from typing import Any

import requests

from ttg_checker.config import WxPusherConfig


class WxPusherNotifier:
    def __init__(self, config: WxPusherConfig) -> None:
        self.config = config

    def send(self, summary: str, content: str) -> dict[str, Any]:
        payload = {
            "appToken": self.config.app_token,
            "content": content,
            "summary": summary,
            "contentType": 1,
            "uids": [self.config.uid],
        }
        if self.config.topic_ids:
            payload["topicIds"] = self.config.topic_ids

        response = requests.post(self.config.base_url, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 1000:
            raise RuntimeError(f"WxPusher send failed: {data}")
        return data
