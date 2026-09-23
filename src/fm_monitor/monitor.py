from __future__ import annotations

from dataclasses import dataclass
import logging
from xml.etree import ElementTree
from urllib import request

from .config import Settings
from .notifier import PushNotifier
from .storage import Storage

logger = logging.getLogger(__name__)


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
            provider=settings.notification_provider,
            endpoint=settings.push_endpoint,
            token=(settings.line_access_token if settings.notification_provider in {"line", "line-broadcast"} else settings.push_token),
            topic=settings.push_topic,
            timeout=settings.request_timeout,
            line_to=settings.line_to,
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
        except Exception as error:
            logger.warning("Push通知に失敗しました。処理は継続します: %s", error)
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

        tokyo = None
        for data in root.findall(".//stream_url/data"):
            direct_area = data.find("area")
            if _is_tokyo(direct_area):
                tokyo = data
                break
            nested_area = next((element for element in data.iter() if _is_tokyo(element)), None)
            if nested_area is not None:
                tokyo = nested_area
                break

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


def _is_tokyo(element: ElementTree.Element | None) -> bool:
    if element is None:
        return False
    text = (element.text or "").strip().lower()
    return text in {"tokyo", "東京"}


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
