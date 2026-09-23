from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from fm_monitor.config import Settings
from fm_monitor.monitor import Monitor
from fm_monitor.storage import Storage


class FakeNotifier:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def send(self, message: str) -> None:
        self.messages.append(message)


class FailingNotifier(FakeNotifier):
    def send(self, message: str) -> None:
        raise RuntimeError("notification failed")


def settings(database_path: Path) -> Settings:
    return Settings(
        target_url="https://example.com/radio",
        database_path=database_path,
        request_timeout=5,
        user_agent="test",
        push_endpoint="https://push.example.test",
        push_token="",
        push_topic="",
    )


class MonitorTest(unittest.TestCase):
    def test_first_run_is_treated_as_changed(self) -> None:
        database_path = Path(self._testMethodName + ".sqlite3")
        notifier = FakeNotifier()
        monitor = Monitor(settings(database_path), Storage(database_path), notifier)

        with patch.object(monitor, "fetch_stream_url", return_value="https://stream.example/one.m3u8"):
            result = monitor.run_once()

        self.assertEqual(result.status, "changed")
        self.assertEqual(notifier.messages, ["ストリームURLに変更がありました。"])
        database_path.unlink()


    def test_same_url_writes_unchanged_log(self) -> None:
        database_path = Path(self._testMethodName + ".sqlite3")
        storage = Storage(database_path)
        storage.initialize()
        storage.save_stream_url("https://stream.example/one.m3u8")
        notifier = FakeNotifier()
        monitor = Monitor(settings(database_path), storage, notifier)

        with patch.object(monitor, "fetch_stream_url", return_value="https://stream.example/one.m3u8"):
            result = monitor.run_once()

        self.assertEqual(result.status, "unchanged")
        self.assertEqual(notifier.messages, [])
        database_path.unlink()


    def test_changed_url_notifies_and_updates_state(self) -> None:
        database_path = Path(self._testMethodName + ".sqlite3")
        storage = Storage(database_path)
        storage.initialize()
        storage.save_stream_url("https://stream.example/one.m3u8")
        notifier = FakeNotifier()
        monitor = Monitor(settings(database_path), storage, notifier)

        with patch.object(monitor, "fetch_stream_url", return_value="https://stream.example/two.m3u8"):
            result = monitor.run_once()

        self.assertEqual(result.status, "changed")
        self.assertEqual(notifier.messages, ["ストリームURLに変更がありました。"])
        self.assertEqual(storage.get_stream_url(), "https://stream.example/two.m3u8")
        database_path.unlink()

    def test_push_failure_does_not_stop_url_update(self) -> None:
        database_path = Path(self._testMethodName + ".sqlite3")
        storage = Storage(database_path)
        storage.initialize()
        notifier = FailingNotifier()
        monitor = Monitor(settings(database_path), storage, notifier)

        with patch.object(monitor, "fetch_stream_url", return_value="https://stream.example/new.m3u8"):
            result = monitor.run_once()

        self.assertEqual(result.status, "changed")
        self.assertEqual(storage.get_stream_url(), "https://stream.example/new.m3u8")
        database_path.unlink()

    def test_fetches_tokyo_fmhls_from_xml(self) -> None:
        database_path = Path(self._testMethodName + ".sqlite3")
        monitor = Monitor(settings(database_path), Storage(database_path), FakeNotifier())
        xml = b"""<radiru_config><stream_url><data><areajp><area>\xe6\x9d\xb1\xe4\xba\xac<fmhls>https://stream.example/tokyo.m3u8</fmhls></area></areajp></data></stream_url></radiru_config>"""
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = xml

        with patch("fm_monitor.monitor.request.urlopen", return_value=response):
            stream_url = monitor.fetch_stream_url()

        print(f"取得したストリームURL: {stream_url}")
        self.assertEqual(stream_url, "https://stream.example/tokyo.m3u8")
        database_path.unlink(missing_ok=True)
