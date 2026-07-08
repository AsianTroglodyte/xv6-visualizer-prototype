#!/usr/bin/env python3

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import os
import re
import subprocess
import sys
import time
import threading
import queue
from dataclasses import dataclass, field

from tkinter import Canvas, PhotoImage, Tk, TclError
from PIL import Image, ImageDraw, ImageFont


PGSIZE = 4096


@dataclass
class Page:
    pid: int
    va: int
    pa: int
    flags: int


@dataclass
class ProcSnap:
    pid: int
    state: str
    name: str
    sz: int
    sp: int
    pages: list[Page] = field(default_factory=list)


@dataclass
class Snapshot:
    seq: int
    procs: list[ProcSnap]


BEGIN_RE = re.compile(r"BEGIN VIZSNAP (\d+)")
END_RE = re.compile(r"END VIZSNAP (\d+)")
PROC_RE = re.compile(
    r"PROC pid=(?P<pid>\d+) state=(?P<state>.+?) name=(?P<name>\S+) "
    r"sz=(?P<sz>\d+) sp=(?P<sp>0x[0-9a-fA-F]+|\d+)"
)
PAGE_RE = re.compile(
    r"PAGE pid=(?P<pid>\d+) va=(?P<va>0x[0-9a-fA-F]+|\d+) "
    r"pa=(?P<pa>0x[0-9a-fA-F]+|\d+) flags=(?P<flags>[0-9a-fA-F]+)"
)


def parse_int(value: str) -> int:
  return int(value, 0)


def classify_role(page: Page, proc: ProcSnap) -> str:
  stack_va = (proc.sp // PGSIZE) * PGSIZE
  if page.va == stack_va:
    return "stack"
  if page.flags & 0x8:
    return "code"
  if page.flags & 0x4:
    return "heap"
  return "other"


def color_for_pid(pid: int) -> str:
  digest = hashlib.sha1(str(pid).encode("ascii")).digest()
  r = 110 + digest[0] % 100
  g = 110 + digest[1] % 100
  b = 110 + digest[2] % 100
  return f"#{r:02x}{g:02x}{b:02x}"


def helper_tint(name: str) -> float:
  if name in {"sh", "memviz"}:
    return 0.55
  return 1.0


def shade(color: str, factor: float) -> str:
  color = color.lstrip("#")
  r = int(color[0:2], 16)
  g = int(color[2:4], 16)
  b = int(color[4:6], 16)
  r = min(255, max(0, int(r * factor + 255 * (1 - factor))))
  g = min(255, max(0, int(g * factor + 255 * (1 - factor))))
  b = min(255, max(0, int(b * factor + 255 * (1 - factor))))
  return f"#{r:02x}{g:02x}{b:02x}"


def escape(text: str) -> str:
  return (
      text.replace("&", "&amp;")
      .replace("<", "&lt;")
      .replace(">", "&gt;")
      .replace('"', "&quot;")
  )


def render_svg(snapshot: Snapshot, output_path: str) -> None:
  procs, width, height, layout = snapshot_layout(snapshot)
  left_margin = 20
  top_margin = 84

  lines = [
      '<?xml version="1.0" encoding="UTF-8"?>',
      f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
      '<rect width="100%" height="100%" fill="#f7f7f3"/>',
      f'<text x="{left_margin}" y="30" font-family="monospace" font-size="24" fill="#111">xv6 page ownership snapshot {snapshot.seq}</text>',
      f'<text x="{left_margin}" y="54" font-family="monospace" font-size="14" fill="#444">user pages grouped by process; role inferred from xv6 address layout</text>',
      f'<rect x="{left_margin}" y="64" width="{width - 2 * left_margin}" height="12" rx="4" fill="#d9dde1"/>',
      f'<text x="{left_margin}" y="62" font-family="monospace" font-size="12" fill="#555">kernel blanket</text>',
  ]

  for proc, x in layout:
    base = color_for_pid(proc.pid)
    tint = helper_tint(proc.name)
    header = shade(base, tint)
    lines.extend([
        f'<rect x="{x}" y="{top_margin}" width="224" height="54" rx="8" fill="{header}" stroke="#333" stroke-width="1.2"/>',
        f'<text x="{x + 12}" y="{top_margin + 20}" font-family="monospace" font-size="16" fill="#111">PID {proc.pid} {escape(proc.name)}</text>',
        f'<text x="{x + 12}" y="{top_margin + 38}" font-family="monospace" font-size="12" fill="#111">{escape(proc.state)} sz={proc.sz}</text>',
    ])

    pages = sorted(proc.pages, key=lambda p: (classify_role(p, proc), p.va))
    for row, page in enumerate(pages):
      y = top_margin + 54 + 12 + row * (26 + 6)
      role = classify_role(page, proc)
      role_fill = {
          "code": "#eef4ff",
          "heap": "#eef7ee",
          "stack": "#fff0e6",
          "other": "#f0f0f0",
      }[role]
      lines.extend([
          f'<rect x="{x}" y="{y}" width="224" height="26" rx="6" fill="{role_fill}" stroke="{base}" stroke-width="1.2"/>',
          f'<text x="{x + 10}" y="{y + 17}" font-family="monospace" font-size="12" fill="#111">{role} va={page.va:#x}</text>',
      ])

  lines.append("</svg>")

  with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))


def snapshot_layout(snapshot: Snapshot):
  procs = sorted(snapshot.procs, key=lambda p: (p.name, p.pid))
  col_w = 240
  header_h = 54
  row_h = 26
  page_gap = 6
  top_margin = 84
  left_margin = 20
  width = max(760, left_margin * 2 + max(1, len(procs)) * col_w)
  max_pages = max((len(p.pages) for p in procs), default=0)
  height = top_margin + header_h + max_pages * (row_h + page_gap) + 80
  layout = [(proc, left_margin + idx * col_w) for idx, proc in enumerate(procs)]
  return procs, width, height, layout


def render_png(snapshot: Snapshot, output_path: str):
  procs, width, height, layout = snapshot_layout(snapshot)
  img = Image.new("RGB", (width, height), "#f7f7f3")
  draw = ImageDraw.Draw(img)
  font_title = ImageFont.load_default()
  font_body = ImageFont.load_default()
  left_margin = 20
  top_margin = 84

  draw.text((left_margin, 18), f"xv6 page ownership snapshot {snapshot.seq}", fill="#111", font=font_title)
  draw.text((left_margin, 42), "user pages grouped by process; role inferred from xv6 address layout", fill="#444", font=font_body)
  draw.rounded_rectangle((left_margin, 64, width - left_margin, 76), radius=4, fill="#d9dde1")
  draw.text((left_margin, 58), "kernel blanket", fill="#555", font=font_body)

  for proc, x in layout:
    base = color_for_pid(proc.pid)
    tint = helper_tint(proc.name)
    header = shade(base, tint)
    draw.rounded_rectangle((x, top_margin, x + 224, top_margin + 54), radius=8, fill=header, outline="#333", width=1)
    draw.text((x + 12, top_margin + 8), f"PID {proc.pid} {proc.name}", fill="#111", font=font_body)
    draw.text((x + 12, top_margin + 28), f"{proc.state} sz={proc.sz}", fill="#111", font=font_body)

    pages = sorted(proc.pages, key=lambda p: (classify_role(p, proc), p.va))
    for row, page in enumerate(pages):
      y = top_margin + 54 + 12 + row * (26 + 6)
      role = classify_role(page, proc)
      role_fill = {
          "code": "#eef4ff",
          "heap": "#eef7ee",
          "stack": "#fff0e6",
          "other": "#f0f0f0",
      }[role]
      draw.rounded_rectangle((x, y, x + 224, y + 26), radius=6, fill=role_fill, outline=base, width=1)
      draw.text((x + 10, y + 7), f"{role} va={page.va:#x}", fill="#111", font=font_body)

  img.save(output_path)
  return img


def parse_snapshot(stream_lines: list[str]) -> Snapshot | None:
  current_seq = None
  procs: list[ProcSnap] = []
  by_pid: dict[int, ProcSnap] = {}

  for raw in stream_lines:
    line = raw.strip()
    if not line:
      continue
    m = BEGIN_RE.search(line)
    if m:
      current_seq = int(m.group(1))
      procs = []
      by_pid = {}
      continue
    m = PROC_RE.search(line)
    if m:
      proc = ProcSnap(
          pid=int(m.group("pid")),
          state=m.group("state"),
          name=m.group("name"),
          sz=int(m.group("sz")),
          sp=parse_int(m.group("sp")),
      )
      procs.append(proc)
      by_pid[proc.pid] = proc
      continue
    m = PAGE_RE.search(line)
    if m:
      pid = int(m.group("pid"))
      proc = by_pid.get(pid)
      if proc is None:
        continue
      proc.pages.append(
          Page(
              pid=pid,
              va=parse_int(m.group("va")),
              pa=parse_int(m.group("pa")),
              flags=int(m.group("flags"), 16),
          )
      )
      continue
    m = END_RE.search(line)
    if m and current_seq is not None:
      return Snapshot(seq=current_seq, procs=procs)

  return None


def wait_for_prompt(proc: subprocess.Popen, timeout: float = 10.0) -> None:
  deadline = time.time() + timeout
  buf = ""
  while time.time() < deadline:
    chunk = proc.stdout.readline()
    if not chunk:
      continue
    buf += chunk
    if "$ " in buf or "init: starting sh" in buf:
      return
  raise RuntimeError("qemu shell did not become ready")


def main() -> int:
  parser = argparse.ArgumentParser(description="Render a live xv6 process snapshot")
  parser.add_argument("--output", default="procviz.svg", help="output SVG path")
  parser.add_argument("--runtime", type=int, default=12, help="seconds to collect snapshots")
  parser.add_argument("--poll", type=int, default=10, help="snapshot interval in ticks")
  parser.add_argument("--children", type=int, default=2, help="number of vizwork children")
  parser.add_argument("--window", action="store_true", help="show a live desktop window")
  args = parser.parse_args()

  if args.window and args.poll == 10:
    args.poll = 1

  proc = subprocess.Popen(
      ["make", "qemu"],
      stdin=subprocess.PIPE,
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
      text=True,
      bufsize=1,
  )

  try:
    png_output = os.path.splitext(args.output)[0] + ".png"
    window_w = 1480
    window_h = 420
    wait_for_prompt(proc)
    proc.stdin.write(f"memviz {args.poll} &\n")
    proc.stdin.write(f"vizwork {args.children} &\n")
    proc.stdin.flush()

    q: queue.Queue[Snapshot] = queue.Queue()
    stop = threading.Event()

    def reader():
      buffer: list[str] = []
      while not stop.is_set():
        line = proc.stdout.readline()
        if not line:
          break
        buffer.append(line)
        if END_RE.search(line):
          snapshot = parse_snapshot(buffer)
          buffer = []
          if snapshot is not None:
            q.put(snapshot)

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()

    latest: Snapshot | None = None
    img = None

    if args.window:
      try:
        root = Tk()
      except TclError:
        sys.stderr.write("no display available; falling back to file output\n")
        sys.stderr.flush()
        args.window = False
      else:
        root.title("xv6 page visualization")
        root.geometry(f"{window_w}x{window_h}")
        root.resizable(False, False)
        canvas = Canvas(root, width=window_w, height=window_h, highlightthickness=0, bg="#f7f7f3")
        canvas.pack(fill="both", expand=True)
        image_id = None
        photo = None

        def pump():
          nonlocal latest, img, image_id, photo
          drained = False
          while True:
            try:
              latest = q.get_nowait()
            except queue.Empty:
              break
            drained = True
          if drained and latest is not None:
            render_svg(latest, args.output)
            img = render_png(latest, png_output)
            scaled = img.copy()
            scaled.thumbnail((window_w, window_h), Image.Resampling.LANCZOS)
            padded = Image.new("RGB", (window_w, window_h), "#f7f7f3")
            offset_x = (window_w - scaled.width) // 2
            offset_y = (window_h - scaled.height) // 2
            padded.paste(scaled, (offset_x, offset_y))
            padded.save(png_output)
            photo = PhotoImage(file=png_output)
            if image_id is None:
              image_id = canvas.create_image(0, 0, image=photo, anchor="nw")
            else:
              canvas.itemconfig(image_id, image=photo)
            canvas.photo = photo
            sys.stderr.write(f"wrote {args.output} and {png_output} for snapshot {latest.seq}\n")
            sys.stderr.flush()
          if proc.poll() is None and not stop.is_set():
            root.after(150, pump)
          else:
            root.after(150, pump)

        root.after(0, pump)
        end_at = time.time() + args.runtime

        def finish():
          if time.time() >= end_at:
            stop.set()
            proc.terminate()
            root.destroy()
          else:
            root.after(250, finish)

        root.after(250, finish)
        root.mainloop()
    else:
      deadline = time.time() + args.runtime
      while time.time() < deadline:
        try:
          latest = q.get(timeout=0.5)
        except queue.Empty:
          continue
        render_svg(latest, args.output)
        sys.stderr.write(f"wrote {args.output} for snapshot {latest.seq}\n")
        sys.stderr.flush()

    if latest is not None:
      if not args.window:
        render_svg(latest, args.output)
      return 0
    sys.stderr.write("no complete snapshot collected\n")
    return 1
  finally:
    stop.set()
    proc.terminate()


if __name__ == "__main__":
  raise SystemExit(main())
