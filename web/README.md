# Browser terminal scaffold

This directory is the first step toward running xv6 in the browser.

Current shape:

- `QEMU` is the eventual WebAssembly target.
- `kernel/kernel` and `fs.img` are host-built assets staged into `build/web/assets/`.
- `index.html`, `styles.css`, and `app.js` provide the local terminal UI.

Planned flow:

1. Build xv6 and `fs.img` on the host.
2. Build QEMU with Emscripten into `qemu.js` and `qemu.wasm`.
3. Load the wasm runtime plus the xv6 assets into the browser.
4. Bridge terminal input/output between the browser UI and QEMU stdio.

This scaffold currently runs as a stub terminal and is meant to be wired to the wasm backend later.
