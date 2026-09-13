"""Shared low-level Chrome DevTools Protocol plumbing.

Headless Chrome rather than Playwright — already on the machine, no browser
download. This was written three times before it was written here: once in
`tools/contact_sheet.py` (screenshot capture), once in `tools/perf_census.py`
(real-page performance measurement, which imported the socket/JSON-RPC
pieces back out of `contact_sheet` rather than duplicating them outright),
and now a third time for `app.adapters.site_fetch.ChromeSiteFetcher`, which
needs the identical "launch Chrome, open a CDP WebSocket, send and receive
JSON-RPC frames" plumbing to do something neither tool does: navigate to a
real `http(s)://` URL rather than a local fixture file, so a page that draws
itself with JavaScript is read the way a visitor's browser sees it, not the
way the raw HTTP response reads.

One implementation. `chrome()`, `_ws_handshake`, `_ws_send`, and `_ws_recv`
are the primitives every caller needs identically; `cdp_session()`
generalises `contact_sheet._cdp_session` to accept a `Path` (a local file,
rendered as `file://...`, exactly as before) OR a plain `str` URL, so this
single context manager now serves a fixture screenshot and a live site
fetch alike.
"""

from __future__ import annotations

import base64
import contextlib
import json
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path

CHROME = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
          "/Applications/Chromium.app/Contents/MacOS/Chromium",
          shutil.which("google-chrome") or "",
          shutil.which("chromium") or "")


def chrome() -> str | None:
    return next((path for path in CHROME if path and Path(path).exists()), None)


def _ws_handshake(sock: socket.socket, host: str, port: int, path: str) -> None:
    key = base64.b64encode(os.urandom(16)).decode()
    request = (f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\n"
               f"Upgrade: websocket\r\nConnection: Upgrade\r\n"
               f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
    sock.sendall(request.encode())
    response = b""
    while b"\r\n\r\n" not in response:
        response += sock.recv(4096)


def _ws_send(sock: socket.socket, data: dict) -> None:
    payload = json.dumps(data).encode()
    header = bytearray([0x81])
    mask = os.urandom(4)
    length = len(payload)
    if length < 126:
        header.append(0x80 | length)
    elif length < 65536:
        header.append(0x80 | 126)
        header += struct.pack(">H", length)
    else:
        header.append(0x80 | 127)
        header += struct.pack(">Q", length)
    header += mask
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    sock.sendall(bytes(header) + masked)


def _ws_recv(sock: socket.socket) -> dict:
    while True:
        head = b""
        while len(head) < 2:
            head += sock.recv(2 - len(head))
        length = head[1] & 0x7F
        if length == 126:
            ext = b""
            while len(ext) < 2:
                ext += sock.recv(2 - len(ext))
            length = struct.unpack(">H", ext)[0]
        elif length == 127:
            ext = b""
            while len(ext) < 8:
                ext += sock.recv(8 - len(ext))
            length = struct.unpack(">Q", ext)[0]
        payload = b""
        while len(payload) < length:
            chunk = sock.recv(length - len(payload))
            if not chunk:
                break
            payload += chunk
        opcode = head[0] & 0x0F
        if opcode == 1:
            return json.loads(payload.decode())
        # A ping or other control frame — not a JSON-RPC reply, keep waiting.


def _navigate_target(target: Path | str) -> str:
    return target.resolve().as_uri() if isinstance(target, Path) else target


@contextlib.contextmanager
def cdp_session(binary: str, target: Path | str, width: int, height: int,
                scale: float, timeout: float = 20.0, extra_flags: tuple[str, ...] = (),
                on_event: Callable[[dict], None] | None = None):
    """A Chrome instance with one page open at `target`, and a
    `call(method, params)` function to drive it over the DevTools protocol.

    `target` is a local `Path` (rendered as `file://...`, for a fixture or a
    generated page) or a plain `str` URL (`http(s)://...`, for a live site).

    `on_event`, when given, is called with every unsolicited CDP message
    (a `Network.responseReceived`, a `Page.frameNavigated`) that arrives
    while `call()` is waiting for a different command's reply — the only
    way to observe an event without discarding it, needed by
    `app.adapters.site_fetch.ChromeSiteFetcher` to read the real HTTP
    status of a page it navigates to itself (see below). `None` (the
    default) reproduces the exact original behaviour: every caller before
    this parameter existed silently skipped unsolicited messages, and
    still does.

    `Emulation.setDeviceMetricsOverride` sets the CSS viewport directly and
    is not subject to the CLI `--window-size` flag's floor (`contact_sheet
    .CDP_MIN_WIDTH`) — the same mechanism Playwright/Puppeteer use for
    mobile emulation, reached here over a raw WebSocket rather than a new
    dependency.

    A long-lived Chrome instance rather than one-shot `--screenshot`: a
    fresh `--user-data-dir` makes `--headless=new` hang on exit under
    `--screenshot` specifically. Managing the process ourselves and
    terminating it explicitly on the way out sidesteps that — nothing here
    waits for Chrome to exit on its own.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    with tempfile.TemporaryDirectory(prefix="cdp-") as profile:
        proc = subprocess.Popen(
            [binary, "--headless=new", "--disable-gpu", "--hide-scrollbars",
             f"--remote-debugging-port={port}", f"--user-data-dir={profile}",
             "--host-resolver-rules=MAP fonts.googleapis.com 127.0.0.1,"
             "MAP fonts.gstatic.com 127.0.0.1",
             "--disable-background-networking", "--disable-sync",
             "--disable-default-apps", "--disable-component-update",
             "--metrics-recording-only", "--no-default-browser-check",
             "--no-service-autorun", "--disable-features=Translate,OptimizationHints",
             "--force-prefers-reduced-motion", *extra_flags, "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                try:
                    with urllib.request.urlopen(
                            f"http://127.0.0.1:{port}/json/version", timeout=0.5):
                        break
                except OSError:
                    time.sleep(0.1)
            else:
                raise TimeoutError("devtools endpoint never came up")

            target_req = urllib.request.Request(
                f"http://127.0.0.1:{port}/json/new?{_navigate_target(target)}",
                method="PUT")
            with urllib.request.urlopen(target_req, timeout=5) as r:
                created = json.loads(r.read())
            ws_url = created["webSocketDebuggerUrl"]
            host_port, _, path = ws_url[len("ws://"):].partition("/")
            host, ws_port = host_port.split(":")

            with socket.create_connection((host, int(ws_port)), timeout=timeout) as ws:
                ws.settimeout(timeout)
                _ws_handshake(ws, host, int(ws_port), "/" + path)

                msg_id = 0

                def call(method: str, params: dict | None = None) -> dict:
                    nonlocal msg_id
                    msg_id += 1
                    _ws_send(ws, {"id": msg_id, "method": method,
                                  "params": params or {}})
                    while True:
                        response = _ws_recv(ws)
                        if response.get("id") == msg_id:
                            return response
                        # An unsolicited event (e.g. Page.frameNavigated) —
                        # not the answer to this call. Handed to `on_event`
                        # when a caller asked to see it, then keep waiting.
                        if on_event is not None and "id" not in response:
                            on_event(response)

                call("Page.enable")
                call("Emulation.setDeviceMetricsOverride", {
                    "width": width, "height": height,
                    "deviceScaleFactor": scale, "mobile": True})
                # The page was requested via `/json/new`'s own URL
                # parameter, which can already be complete by the time the
                # WebSocket connects — poll readiness rather than waiting on
                # a load event that may already have fired.
                ready_deadline = time.monotonic() + timeout
                while time.monotonic() < ready_deadline:
                    state = call("Runtime.evaluate", {
                        "expression": "document.readyState",
                        "returnByValue": True})
                    if (state.get("result", {}).get("result", {}).get("value")
                            == "complete"):
                        break
                    time.sleep(0.05)
                yield call
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
