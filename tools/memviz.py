#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from tkinter import Canvas, PhotoImage, Tk, TclError

from PIL import Image, ImageDraw, ImageFont

from procviz import (
    BEGIN_RE,
    END_RE,
    PAGE_RE,
    PROC_RE,
    Snapshot,
    classify_role,
    color_for_pid,
    escape,
    helper_tint,
    shade,
    parse_snapshot,
    wait_for_prompt,
)


PGSIZE = 4096


@dataclass
class Cell:
  pid: int
  name: str
  state: str
  va: int
  pa: int
  role: str
  color: str


def collect_cells(snapshot: Snapshot) -> list[Cell]:
  cells: list[Cell] = []
  for proc in snapshot.procs:
    base = color_for_pid(proc.pid)
    color = shade(base, helper_tint(proc.name))
    for page in proc.pages:
      cells.append(
          Cell(
              pid=proc.pid,
              name=proc.name,
              state=proc.state,
              va=page.va,
              pa=page.pa,
              role=classify_role(page, proc),
              color=color,
          )
      )
  cells.sort(key=lambda c: (c.pa, c.pid, c.va))
  return cells


def column_groups(cells: list[Cell], per_col: int) -> list[list[Cell]]:
  return [cells[i:i + per_col] for i in range(0, len(cells), per_col)]


def column_dimensions(cells: list[Cell], per_col: int):
  columns = column_groups(cells, per_col)
  header_h = 20
  row_h = 18
  segment_gap = 12
  col_widths = [72, 112, 96, 120, 120]
  segment_width = sum(col_widths)
  width = max(1080, 40 + len(columns) * segment_width + max(0, len(columns) - 1) * segment_gap)
  height = 96 + header_h + max(1, per_col) * row_h + 36
  return columns, width, height, col_widths, header_h, row_h, segment_gap


def role_fill(role: str) -> str:
  return {
      "code": "#eef4ff",
      "heap": "#eef7ee",
      "stack": "#fff0e6",
      "other": "#f0f0f0",
  }[role]


def render_svg(snapshot: Snapshot, output_path: str) -> None:
  cells = collect_cells(snapshot)
  columns, width, height, col_widths, header_h, row_h, segment_gap = column_dimensions(cells, 12)
  left_margin = 20

  lines = [
      '<?xml version="1.0" encoding="UTF-8"?>',
      f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
      '<rect width="100%" height="100%" fill="#f7f7f3"/>',
      f'<text x="{left_margin}" y="30" font-family="monospace" font-size="24" fill="#111">xv6 physical memory line snapshot {snapshot.seq}</text>',
      f'<text x="{left_margin}" y="54" font-family="monospace" font-size="14" fill="#444">pages sorted by physical address; each page is a compact table row</text>',
      f'<rect x="{left_margin}" y="64" width="{width - 2 * left_margin}" height="12" rx="4" fill="#d9dde1"/>',
      f'<text x="{left_margin}" y="62" font-family="monospace" font-size="12" fill="#555">kernel blanket / unreported memory</text>',
  ]

  y0 = 96
  x0 = left_margin
  headers = ["PID", "Name", "Role", "VA", "PA"]
  segment_width = sum(col_widths)
  for seg_idx, segment in enumerate(columns):
    seg_x = x0 + seg_idx * (segment_width + segment_gap)
    x = seg_x
    for title, w in zip(headers, col_widths):
      lines.extend([
          f'<rect x="{x}" y="{y0}" width="{w}" height="{header_h}" fill="#e6e6de" stroke="#bcbcb2" stroke-width="1"/>',
          f'<text x="{x + 8}" y="{y0 + 14}" font-family="monospace" font-size="11" fill="#222">{title}</text>',
      ])
      x += w

    for row_idx, cell in enumerate(segment):
      y = y0 + header_h + row_idx * row_h
      values = [
          str(cell.pid),
          cell.name,
          cell.role,
          f"{cell.va:#x}",
          f"{cell.pa:#x}",
      ]
      lines.append(f'<rect x="{seg_x}" y="{y}" width="{segment_width}" height="{row_h}" fill="{role_fill(cell.role)}" stroke="#c8c8c0" stroke-width="1"/>')
      x = seg_x
      for w in col_widths[:-1]:
        x += w
        lines.append(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + row_h}" stroke="#d6d6cf" stroke-width="1"/>')
      x = seg_x
      for value, w in zip(values, col_widths):
        lines.append(f'<text x="{x + 8}" y="{y + 13}" font-family="monospace" font-size="10" fill="#111">{escape(value)}</text>')
        x += w

  lines.append("</svg>")

  with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))


def render_png(snapshot: Snapshot, output_path: str):
  cells = collect_cells(snapshot)
  columns, width, height, col_widths, header_h, row_h, segment_gap = column_dimensions(cells, 12)
  img = Image.new("RGB", (width, height), "#f7f7f3")
  draw = ImageDraw.Draw(img)
  font_title = ImageFont.load_default()
  font_body = ImageFont.load_default()
  left_margin = 20

  draw.text((left_margin, 18), f"xv6 physical memory line snapshot {snapshot.seq}", fill="#111", font=font_title)
  draw.text((left_margin, 42), "pages sorted by physical address; each page is a compact table row", fill="#444", font=font_body)
  draw.rounded_rectangle((left_margin, 64, width - left_margin, 76), radius=4, fill="#d9dde1")
  draw.text((left_margin, 58), "kernel blanket / unreported memory", fill="#555", font=font_body)

  y0 = 96
  x0 = left_margin
  headers = ["PID", "Name", "Role", "VA", "PA"]
  segment_width = sum(col_widths)
  for seg_idx, segment in enumerate(columns):
    seg_x = x0 + seg_idx * (segment_width + segment_gap)
    x = seg_x
    for title, w in zip(headers, col_widths):
      draw.rectangle((x, y0, x + w, y0 + header_h), fill="#e6e6de", outline="#bcbcb2", width=1)
      draw.text((x + 8, y0 + 5), title, fill="#222", font=font_body)
      x += w

    for row_idx, cell in enumerate(segment):
      y = y0 + header_h + row_idx * row_h
      values = [
          str(cell.pid),
          cell.name,
          cell.role,
          f"{cell.va:#x}",
          f"{cell.pa:#x}",
      ]
      draw.rectangle((seg_x, y, seg_x + segment_width, y + row_h), fill=role_fill(cell.role), outline="#c8c8c0", width=1)
      x = seg_x
      for w in col_widths[:-1]:
        x += w
        draw.line((x, y, x, y + row_h), fill="#d6d6cf", width=1)
      x = seg_x
      for value, w in zip(values, col_widths):
        draw.text((x + 8, y + 3), value, fill="#111", font=font_body)
        x += w

  img.save(output_path)
  return img


def main() -> int:
  parser = argparse.ArgumentParser(description="Render xv6 physical memory as a live table")
  parser.add_argument("--output", default="memviz.svg", help="output SVG path")
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
    window_w = 1600
    window_h = 560
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

    if args.window:
      try:
        root = Tk()
      except TclError:
        sys.stderr.write("no display available; falling back to file output\n")
        sys.stderr.flush()
        args.window = False
      else:
        root.title("xv6 physical memory line")
        root.geometry(f"{window_w}x{window_h}")
        root.resizable(False, False)
        canvas = Canvas(root, width=window_w, height=window_h, highlightthickness=0, bg="#f7f7f3")
        canvas.pack(fill="both", expand=True)
        image_id = None
        photo = None

        def pump():
          nonlocal latest, image_id, photo
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
