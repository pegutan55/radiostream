from __future__ import annotations

import argparse
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

from .config import load_settings
from .monitor import Monitor
from .storage import Storage
from .sync import LogSynchronizer


def main() -> int:
    parser = argparse.ArgumentParser(description="FMラジオストリームURL変更検知")
    parser.add_argument("--config", type=Path, default=Path("config.ini"))
    parser.add_argument("--once", action="store_true", help="1回だけ実行して終了")
    parser.add_argument("--sync", action="store_true", help="D1へ未同期ログを送信して終了")
    parser.add_argument("--at", default="03:00", help="常駐実行時の毎日の実行時刻 (HH:MM)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    settings = load_settings(args.config)
    storage = Storage(settings.database_path)
    if args.sync:
        result = LogSynchronizer(settings, storage).run_once()
        logging.info("D1同期: %d件送信、最後の同期ID=%d", result.sent, result.last_synced_log_id)
        return 0

    monitor = Monitor(settings, storage)
    if args.once:
        result = monitor.run_once()
        logging.info("%s: %s", result.status, result.message.replace("\n", " "))
        return 0

    while True:
        wait_seconds = _seconds_until(args.at)
        logging.info("次回実行まで%d秒待機します", wait_seconds)
        time.sleep(wait_seconds)
        try:
            result = monitor.run_once()
            logging.info("%s: %s", result.status, result.message.replace("\n", " "))
        except Exception:
            logging.exception("FMストリームURLの確認に失敗しました")


def _seconds_until(schedule_time: str) -> int:
    try:
        hour, minute = (int(value) for value in schedule_time.split(":", 1))
        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            raise ValueError
    except ValueError as error:
        raise ValueError("--atにはHH:MM形式の時刻を指定してください") from error

    now = datetime.now()
    next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if next_run <= now:
        next_run += timedelta(days=1)
    return max(1, int((next_run - now).total_seconds()))


if __name__ == "__main__":
    raise SystemExit(main())
