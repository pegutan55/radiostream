from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import configparser
from urllib.parse import urlparse


@dataclass(frozen=True)
class Settings:
    target_url: str
    database_path: Path
    request_timeout: float
    user_agent: str
    notification_provider: str
    push_endpoint: str
    push_token: str
    push_topic: str
    line_access_token: str
    line_to: str


def load_settings(path: Path) -> Settings:
    parser = configparser.ConfigParser()
    if not parser.read(path, encoding="utf-8"):
        raise FileNotFoundError(f"設定ファイルが見つかりません: {path}")

    source = parser["source"]
    storage = parser["storage"]
    notification = parser["notification"]
    target_url = source.get("target_url", "").strip()
    if urlparse(target_url).scheme not in {"http", "https"}:
        raise ValueError("source.target_urlにはhttpまたはhttpsのURLを指定してください")

    return Settings(
        target_url=target_url,
        database_path=Path(storage.get("database_path", "data/radiostream.sqlite3")),
        request_timeout=source.getfloat("request_timeout", fallback=20.0),
        user_agent=source.get("user_agent", "radiostream-monitor/1.0"),
        notification_provider=notification.get("provider", "ntfy").strip().lower(),
        push_endpoint=notification.get("endpoint", "").strip(),
        push_token=notification.get("token", "").strip(),
        push_topic=notification.get("topic", "").strip(),
        line_access_token=notification.get("access_token", "").strip(),
        line_to=notification.get("to", "").strip(),
    )
