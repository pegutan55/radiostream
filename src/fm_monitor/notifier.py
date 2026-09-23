from __future__ import annotations

from dataclasses import dataclass
import json
from urllib import request


@dataclass(frozen=True)
class PushNotifier:
    endpoint: str
    provider: str = "ntfy"
    token: str = ""
    topic: str = ""
    timeout: float = 20.0
    line_to: str = ""

    def send(self, message: str) -> None:
        if self.provider in {"line", "line-broadcast"}:
            if self.provider == "line-broadcast":
                self._send_line_broadcast(message)
                return
            self._send_line(message)
            return
        if not self.endpoint:
            raise ValueError("Push通知のendpointが設定されていません")

        headers = {"Content-Type": "text/plain; charset=utf-8"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.topic:
            headers["X-Topic"] = self.topic
        request_data = request.Request(
            self.endpoint,
            data=message.encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with request.urlopen(request_data, timeout=self.timeout) as response:
            if response.status >= 400:
                raise RuntimeError(f"Push通知に失敗しました: HTTP {response.status}")

    def _send_line(self, message: str) -> None:
        if not self.token:
            raise ValueError("LINE Messaging APIのaccess_tokenが設定されていません")
        if not self.line_to:
            raise ValueError("LINE Messaging APIのtoが設定されていません")

        payload = {
            "to": self.line_to,
            "messages": [{"type": "text", "text": message}],
        }
        request_data = request.Request(
            "https://api.line.me/v2/bot/message/push",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with request.urlopen(request_data, timeout=self.timeout) as response:
            if response.status >= 400:
                raise RuntimeError(f"LINE Push通知に失敗しました: HTTP {response.status}")

    def _send_line_broadcast(self, message: str) -> None:
        if not self.token:
            raise ValueError("LINE Messaging APIのaccess_tokenが設定されていません")

        payload = {"messages": [{"type": "text", "text": message}]}
        request_data = request.Request(
            "https://api.line.me/v2/bot/message/broadcast",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with request.urlopen(request_data, timeout=self.timeout) as response:
            if response.status >= 400:
                raise RuntimeError(f"LINE Broadcast通知に失敗しました: HTTP {response.status}")
