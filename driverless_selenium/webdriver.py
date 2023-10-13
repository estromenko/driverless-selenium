import json
import os
import signal
import socket
import subprocess
import time
from pathlib import Path
from types import TracebackType
from typing import Any, Self

import cdp
import cdp.dom
import cdp.page
import cdp.target
import requests
from cdp.dom import Node
from cdp.target import TargetID
from selenium.webdriver import ChromeOptions
from websockets.sync.client import ClientConnection, connect


class Chrome:
    def __init__(self: Self, options: ChromeOptions | None = None) -> None:
        self.conn: ClientConnection
        self.options: ChromeOptions = options or ChromeOptions()
        self.target_id: str | None = None
        self.browser_pid: int | None = None
        self._debugger_address: str | None = None

    def __enter__(self: Self) -> Self:
        return self

    def __exit__(
        self: Self,
        typ: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
        extra_arg: int = 0,
    ) -> None:
        self.conn.close()
        if self.browser_pid:
            os.kill(self.browser_pid, signal.SIGTERM)

    def __del__(self: Self) -> None:
        if self.browser_pid:
            os.kill(self.browser_pid, signal.SIGTERM)

    @staticmethod
    def _get_random_available_port() -> int:
        sock = socket.socket()
        sock.bind(("", 0))
        return sock.getsockname()[1]

    _chrome_location_candidates = (
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/local/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/local/bin/google-chrome",
    )

    def _execute_command(self: Self, command: Any) -> dict:  # noqa: ANN401
        """Execute provided command and receives its result."""
        request = next(command)
        request["id"] = 0
        self.conn.send(json.dumps(request))
        return json.loads(self.conn.recv())

    def _find_browser_executable_name(self: Self) -> str:
        """Find the path to Chrome installed on the system."""
        for candidate in self._chrome_location_candidates:
            if Path(candidate).exists():
                return candidate
        error_message = "Chrome is not installed"
        raise FileExistsError(error_message)

    def _start_browser(self: Self) -> None:
        browser_executable_name = self._find_browser_executable_name()
        port = self._get_random_available_port()

        self.options.add_argument(f"--remote-debugging-port={port}")

        browser = subprocess.Popen(
            [browser_executable_name, *self.options.arguments],  # noqa: S603
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
        )
        self.browser_pid = browser.pid

        self._debugger_address = f"127.0.0.1:{port}"

    def _get_target_id(self: Self) -> str:
        response = requests.get(f"http://{self._debugger_address}/json", timeout=10)
        return response.json()[0]["id"]

    def _connect_to_session(self: Self) -> None:
        time.sleep(2)

        if not self._debugger_address:
            return

        self.target_id = self._get_target_id()
        self.conn = connect(f"ws://{self._debugger_address}/devtools/page/{self.target_id}")

        self._execute_command(cdp.target.activate_target(TargetID(self.target_id)))

    def get(self: Self, url: str) -> None:
        if not self.browser_pid:
            self._start_browser()
            self._connect_to_session()

        self._execute_command(cdp.page.enable())
        self._execute_command(cdp.page.navigate(url))

    @property
    def page_source(self: Self) -> Node:
        return Node.from_json(self._execute_command(cdp.dom.get_document()))

    @property
    def get_current_url(self: Self) -> str:
        """Возвращает url текущей страницы."""
        return self._execute_command(cdp.page.get_app_manifest())["url"]
