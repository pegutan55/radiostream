from __future__ import annotations

from dataclasses import dataclass
from xml.etree import ElementTree
from urllib import request

from .config import Settings
from .notifier import PushNotifier
from .storage import Storage


@dataclass(frozen=True)
class MonitorResult:
    status: str
    stream_url: str
    message: str


class Monitor:
    def __init__(
        self,
        settings: Settings,
        storage: Storage,
        notifier: PushNotifier | None = None,
    ) -> None:
        self.settings = settings
        self.storage = storage
        self.notifier = notifier or PushNotifier(
            settings.push_endpoint,
            settings.push_token,
            settings.push_topic,
            settings.request_timeout,
        )

    def run_once(self) -> MonitorResult:
        self.storage.initialize()
        current_url = self.fetch_stream_url()
        previous_url = self.storage.get_stream_url()

        if previous_url is not None and previous_url == current_url:
            message = "ストリームURLに変更はありませんでした"
            self.storage.save_log(message)
            return MonitorResult("unchanged", current_url, message)

        message = (
            "ストリームURLに変更がありました。\n"
            f"変更後のストリームURLはこちら。{current_url}"
        )
        self.storage.save_log(message)
        try:
            self.notifier.send("ストリームURLに変更がありました。")
        except Exception:
            pass
        self.storage.save_stream_url(current_url)
        return MonitorResult("changed", current_url, message)

    def fetch_stream_url(self) -> str:
        http_request = request.Request(
            self.settings.target_url,
            headers={"User-Agent": self.settings.user_agent},
        )
        with request.urlopen(http_request, timeout=self.settings.request_timeout) as response:
            body = response.read()
        try:
            root = ElementTree.fromstring(body)
        except ElementTree.ParseError as error:
            raise ValueError("ストリームURL管理用XMLを解析できませんでした") from error

        for data in root.findall(".//stream_url/data"):
            area = data.find("area")

            if area is not None and area.text == "tokyo":
                tokyo = data
                break

        # data = _find_child(_find_child(_find_child(root, "stream_url"), "data"), "areajp")
        # tokyo = next(
        #     (element for element in data.iter() if _contains_text_or_attribute(element, "東京")),
        #     None,
        # )
        if tokyo is None:
            raise ValueError("ストリームURL管理用XMLから東京の要素を取得できませんでした")
        stream_url = _find_child(tokyo, "fmhls")
        if not (stream_url.text and stream_url.text.strip()):
            raise ValueError("東京のfmhls要素にストリームURLがありません")
        return stream_url.text.strip()


def _find_child(element: ElementTree.Element | None, name: str) -> ElementTree.Element:
    if element is None:
        raise ValueError(f"XMLに{name}要素がありません")
    for child in element:
        if _local_name(child.tag) == name:
            return child
    raise ValueError(f"XMLに{name}要素がありません")


def _contains_text_or_attribute(element: ElementTree.Element, value: str) -> bool:
    if value in (element.text or ""):
        return True
    return any(value in attribute for attribute in element.attrib.values())


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
