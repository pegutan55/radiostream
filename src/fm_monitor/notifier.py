from __future__ import annotations

from dataclasses import dataclass
from urllib import request


@dataclass(frozen=True)
class PushNotifier:
    endpoint: str
    token: str = ""
    topic: str = ""
    timeout: float = 20.0

    def send(self, message: str) -> None:
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
