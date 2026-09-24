from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from fm_monitor.config import Settings
from fm_monitor.storage import Storage
from fm_monitor.sync import LogSynchronizer


def settings(database_path: Path) -> Settings:
    return Settings(
        target_url="https://example.com/radio",
        database_path=database_path,
        request_timeout=5,
        user_agent="test",
        notification_provider="ntfy",
        push_endpoint="https://push.example.test",
        push_token="",
        push_topic="",
        line_access_token="",
        line_to="",
        sync_endpoint="https://sync.example.test",
        sync_token="test-token",
        sync_source_id="pi-main",
        sync_batch_size=500,
    )


class LogSynchronizerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.database_path = Path(self._testMethodName + ".sqlite3")
        self.storage = Storage(self.database_path)
        self.storage.initialize()
        self.storage.save_log("テストログ")

    def tearDown(self) -> None:
        self.database_path.unlink(missing_ok=True)

    def test_success_updates_cursor_after_sending_logs(self) -> None:
        response = MagicMock(status=200)
        response.__enter__.return_value = response
        with patch("fm_monitor.sync.request.urlopen", return_value=response) as open_url:
            result = LogSynchronizer(settings(self.database_path), self.storage).run_once()

        self.assertEqual(result.sent, 1)
        self.assertEqual(result.last_synced_log_id, 1)
        self.assertEqual(self.storage.get_last_synced_log_id(), 1)
        sent_request = open_url.call_args.args[0]
        self.assertIn('"source_id": "pi-main"', sent_request.data.decode())

    def test_failed_request_keeps_cursor_for_retry(self) -> None:
        with patch(
            "fm_monitor.sync.request.urlopen",
            side_effect=RuntimeError("network failed"),
        ):
            with self.assertRaises(RuntimeError):
                LogSynchronizer(settings(self.database_path), self.storage).run_once()

        self.assertEqual(self.storage.get_last_synced_log_id(), 0)


if __name__ == "__main__":
    unittest.main()