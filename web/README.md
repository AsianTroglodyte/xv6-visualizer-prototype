# xv6 Browser Terminal

This server exposes two browser paths:

- `/` starts one native server-side QEMU/xv6 process per WebSocket connection.
- `/jslinux.html` builds an upstream JSLinux URL whose config points back to
  this server's staged xv6 assets.

The server-side QEMU path uses the already-built `kernel/kernel` and disk
image. It looks for `fs.img` first, then falls back to
`build/web/assets/fs.img`.

Install the Python dependency:

```bash
python3 -m pip install websockets
```

Run the server:

```bash
python3 web/server.py
```

Open:

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/jslinux.html
```

The `ws://127.0.0.1:8765/terminal` endpoint is for the page's JavaScript
client. Opening it directly in a browser tab sends a normal HTTP request to the
WebSocket port and can produce an `InvalidUpgrade` message in the server log.

Each browser tab gets its own QEMU process. Closing the tab or pressing
Disconnect terminates that process.

The server serves `build/web/assets/` at `/assets/` and sends CORS headers so
upstream JSLinux can fetch `xv6-jslinux.cfg`, `kernel`, and the split disk
image generated from `fs.img`.

When `fs.img` changes, refresh the TinyEMU HTTP block files:

```bash
python3 web/stage_jslinux_disk.py
```

JSLinux compatibility note: modern JSLinux is based on TinyEMU. The handoff
config describes a RISC-V VM with `kernel` and `drive0`, but xv6-riscv is built
for QEMU's `virt` machine. If TinyEMU does not boot this kernel directly, use
the server-side QEMU terminal.
