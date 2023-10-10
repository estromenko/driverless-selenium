import asyncio
import os
import signal
import socket
import subprocess
from pathlib import Path
from types import TracebackType

import cdp
import trio_cdp
from trio_cdp.generated import dom, page, target


class ChromeOptions:
    def __init__(self: "ChromeOptions") -> None:
        self.arguments: list[str] = []

    def add_argument(self: "ChromeOptions", argument: str) -> None:
        self.arguments.append(argument)


class Chrome:
    def __init__(self: "Chrome", options: ChromeOptions | None = None) -> None:
        self.options: ChromeOptions = options or ChromeOptions()
        self.session_id: str | None = None
        self.browser_pid: int | None = None
        self.session: trio_cdp.CdpSession | None = None

    def __enter__(self: "Chrome") -> "Chrome":
        return self

    def __exit__(
        self: "Chrome",
        typ: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
        extra_arg: int = 0,
    ) -> None:
        self.conn.close()
        if self.browser_pid:
            os.kill(self.browser_pid, signal.SIGTERM)

    def __del__(self: "Chrome") -> None:
        if self.browser_pid:
            os.kill(self.browser_pid, signal.SIGTERM)

    @staticmethod
    def _get_random_available_port() -> str:
        sock = socket.socket()
        sock.bind(("", 0))
        return str(sock.getsockname()[1])

    _chrome_location_candidates = (
        "/usr/bin/google-chrome",
        "/usr/local/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/local/bin/chromium",
    )

    def _find_browser_executable_name(self: "Chrome") -> str:
        """Find the path to Chrome installed on the system."""
        for candidate in self._chrome_location_candidates:
            if Path(candidate).exists():
                return candidate
        error_message = "Chrome is not installed"
        raise FileExistsError(error_message)

    def _start_browser(self: "Chrome") -> None:
        browser_executable_name = self._find_browser_executable_name()

        browser = subprocess.Popen(
            [browser_executable_name, *self.options.arguments],  # noqa: S603
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
        )
        self.browser_pid = browser.pid

    async def _connect_to_session(self: "Chrome") -> None:
        port = self._get_random_available_port()
        self._debugger_address = f"127.0.0.1:{port}"

        self.conn = anext(trio_cdp.open_cdp(self._debugger_address).gen)
        targets = await target.get_targets()
        self.target_id = targets[0].target_id
        self.session = self.conn.open_session(self.target_id)

    def get(self: "Chrome", url: str) -> None:
        if not self.browser_pid:
            self._start_browser()
            asyncio.run(self._connect_to_session())
        if self.session:
            self.session.page_enable()
            self.session.wait_for(cdp.page.LoadEventFired)
        asyncio.run(page.navigate(url))

    async def find_by_css(self: "Chrome", css_selector: str) -> list[str]:
        nodes = await dom.query_selector_all(self.page_source.node_id, css_selector)
        nodes_html: list[str] = [await dom.get_outer_html(node) for node in nodes]
        return nodes_html

    @property
    def page_source(self: "Chrome") -> cdp.dom.Node:
        return asyncio.run(dom.get_document())

    @property
    def get_current_url(self: "Chrome") -> str:
        """Возвращает url текущей страницы."""
        return asyncio.run(page.get_app_manifest())[0]
