from __future__ import annotations

import json
from dataclasses import dataclass
from urllib import request

from .config import Settings
from .storage import Storage


@dataclass(frozen=True)
class SyncResult:
    sent: int
    last_synced_log_id: int


class LogSynchronizer:
    def __init__(self, settings: Settings, storage: Storage) -> None:
        if not settings.sync_endpoint:
            raise ValueError("sync.endpointが設定されていません")
        if not settings.sync_token:
            raise ValueError("sync.tokenが設定されていません")
        if not settings.sync_source_id:
            raise ValueError("sync.source_idが設定されていません")
        if settings.sync_batch_size < 1 or settings.sync_batch_size > 500:
            raise ValueError("sync.batch_sizeは1から500の範囲で指定してください")
        self.settings = settings
        self.storage = storage

    def run_once(self) -> SyncResult:
        self.storage.initialize()
        last_synced_log_id = self.storage.get_last_synced_log_id()
        logs = self.storage.get_logs_after(
            last_synced_log_id, self.settings.sync_batch_size
        )
        if not logs:
            return SyncResult(0, last_synced_log_id)

        payload = {
            "source_id": self.settings.sync_source_id,
            "logs": [
                {
                    "id": int(log["id"]),
                    "message": log["message"],
                    "executed_at": log["executed_at"],
                }
                for log in logs
            ],
        }
        self._send(payload)
        new_last_id = int(logs[-1]["id"])
        self.storage.save_last_synced_log_id(new_last_id)
        return SyncResult(len(logs), new_last_id)

    def _send(self, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        http_request = request.Request(
            self.settings.sync_endpoint,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.settings.sync_token}",
                "Content-Type": "application/json",
                "User-Agent": self.settings.user_agent,
            },
        )
        with request.urlopen(
            http_request, timeout=self.settings.request_timeout
        ) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError(f"D1同期APIがHTTP {response.status}を返しました")
            response.read()