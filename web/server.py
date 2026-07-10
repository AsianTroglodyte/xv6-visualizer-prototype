#!/usr/bin/env python3
import argparse
import asyncio
import contextlib
import os
import posixpath
import pty
import signal
import subprocess
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

import websockets


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web"
BUILD_WEB_ROOT = ROOT / "build" / "web"


def asset_paths():
    kernel = ROOT / "kernel" / "kernel"
    fs_candidates = [
        ROOT / "fs.img",
        ROOT / "build" / "web" / "assets" / "fs.img",
    ]
    fs = next((path for path in fs_candidates if path.exists()), fs_candidates[0])
    return kernel, fs


class StaticHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".cfg": "text/plain",
    }

    def translate_path(self, path):
        url_path = urlsplit(path).path
        url_path = posixpath.normpath(unquote(url_path))
        parts = [part for part in url_path.split("/") if part and part not in (".", "..")]

        if parts and parts[0] == "assets":
            candidate = BUILD_WEB_ROOT.joinpath(*parts)
        else:
            candidate = WEB_ROOT.joinpath(*parts)
            if not candidate.exists():
                build_candidate = BUILD_WEB_ROOT.joinpath(*parts)
                if build_candidate.exists():
                    candidate = build_candidate

        return str(candidate)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("Cross-Origin-Resource-Policy", "cross-origin")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()


def qemu_command(cpus):
    kernel, fs = asset_paths()
    return [
        "qemu-system-riscv64",
        "-machine", "virt",
        "-bios", "none",
        "-kernel", str(kernel),
        "-m", "128M",
        "-smp", str(cpus),
        "-nographic",
        "-global", "virtio-mmio.force-legacy=false",
        "-drive", f"file={fs},if=none,format=raw,id=x0",
        "-device", "virtio-blk-device,drive=x0,bus=virtio-mmio-bus.0",
    ]


def require_assets():
    missing = []
    for path in asset_paths():
        if not path.exists():
            missing.append(str(path.relative_to(ROOT)))
    if missing:
        raise FileNotFoundError("missing required xv6 asset(s): " + ", ".join(missing))


async def read_pty(master_fd, websocket):
    loop = asyncio.get_running_loop()
    while True:
        try:
            data = await loop.run_in_executor(None, os.read, master_fd, 4096)
        except OSError:
            break
        if not data:
            break
        await websocket.send(data.decode("utf-8", errors="replace"))


async def handle_terminal(websocket, cpus):
    proc = None
    master_fd = None
    slave_fd = None
    reader_task = None

    try:
        require_assets()
        master_fd, slave_fd = pty.openpty()
        proc = subprocess.Popen(
            qemu_command(cpus),
            cwd=ROOT,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            start_new_session=True,
            close_fds=True,
        )
        os.close(slave_fd)
        slave_fd = None

        await websocket.send("[server] started xv6 on QEMU\n")
        reader_task = asyncio.create_task(read_pty(master_fd, websocket))

        async for message in websocket:
            if isinstance(message, bytes):
                os.write(master_fd, message)
            else:
                os.write(master_fd, message.encode())
    except FileNotFoundError as exc:
        await websocket.send(f"[server] {exc}\n")
    except websockets.ConnectionClosed:
        pass
    finally:
        if reader_task:
            reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await reader_task
        if master_fd is not None:
            with contextlib.suppress(OSError):
                os.close(master_fd)
        if slave_fd is not None:
            with contextlib.suppress(OSError):
                os.close(slave_fd)
        if proc and proc.poll() is None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=2)


def serve_static(host, port):
    handler = partial(StaticHandler, directory=str(WEB_ROOT))
    server = ThreadingHTTPServer((host, port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


async def main_async(args):
    static_server = serve_static(args.host, args.http_port)
    print(f"HTTP  http://{args.host}:{args.http_port}/", flush=True)
    print(
        f"WS    ws://{args.host}:{args.ws_port}/terminal "
        "(used by the page; do not open directly)",
        flush=True,
    )

    async def handler(websocket, path=None):
        _ = path
        await handle_terminal(websocket, args.cpus)

    try:
        async with websockets.serve(handler, args.host, args.ws_port, max_size=None):
            await asyncio.Future()
    finally:
        static_server.shutdown()


def main():
    parser = argparse.ArgumentParser(description="Serve a browser terminal backed by xv6 on QEMU.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--http-port", type=int, default=8000)
    parser.add_argument("--ws-port", type=int, default=8765)
    parser.add_argument("--cpus", type=int, default=1)
    args = parser.parse_args()
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
