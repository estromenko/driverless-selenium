import os
import signal
import subprocess
from pathlib import Path
from trio_cdp import open_cdp, page, dom


class ChromeOptions:
    def __init__(self) -> None:
        self.arguments: list[str] = []

    def add_argument(self, argument: str) -> None:
        self.arguments.append(argument)


class Chrome:
    def __init__(self, options: ChromeOptions | None = None) -> None:
        self.options: ChromeOptions = options or ChromeOptions()
        self.session_id: str | None = None
        self.browser_pid: int | None = None

    def __enter__(self) -> 'Chrome':
        return self

    def __exit__(self) -> None:
        if self.browser_pid:
            os.kill(self.browser_pid, signal.SIGTERM)

    def _find_browser_executable_name(self) -> str:
        raise NotImplementedError

    def _start_browser(self) -> None:
        browser_executable_name = self._find_browser_executable_name()

        browser = subprocess.Popen(
            [browser_executable_name, *self.options.arguments],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            close_fds=True,
        )
        self.browser_pid = browser.pid

    def get(self, url: str) -> None:
        raise NotImplementedError
