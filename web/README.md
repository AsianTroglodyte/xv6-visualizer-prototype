# xv6 Server Terminal

This browser terminal starts one server-side QEMU/xv6 process per WebSocket
connection. It uses the already-built `kernel/kernel` and disk image. The
server looks for `fs.img` first, then falls back to `build/web/assets/fs.img`.

Install the only Python dependency:

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
```

The `ws://127.0.0.1:8765/terminal` endpoint is for the page's JavaScript
client. Opening it directly in a browser tab sends a normal HTTP request to the
WebSocket port and can produce an `InvalidUpgrade` message in the server log.

Each browser tab gets its own QEMU process. Closing the tab or pressing
Disconnect terminates that process.
