#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import queue
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from tkinter import Canvas, PhotoImage, Tk, TclError

from PIL import Image, ImageDraw, ImageFont

from procviz import color_for_pid, escape, helper_tint, shade, wait_for_prompt


BEGIN_RE = re.compile(r"BEGIN LOCKTRACE (\d+)")
END_RE = re.compile(r"END LOCKTRACE (\d+)")
EVENT_RE = re.compile(
    r"EVENT seq=(?P<seq>\d+) time=(?P<time>\d+) cpu=(?P<cpu>\d+) "
    r"pid=(?P<pid>-?\d+) kind=(?P<kind>\w+) hold=(?P<hold>\d+) lock=(?P<lock>\S+) name=(?P<name>\S+)"
)

EXCLUDED_NAMES = {"init", "sh", "locktrace"}


@dataclass
class TraceEvent:
  seq: int
  time: int
  cpu: int
  pid: int
  kind: str
  hold: int
  lock: str
  name: str


@dataclass
class ProcTrack:
  pid: int
  name: str
  color: str
  waits: list[tuple[int, int]] = field(default_factory=list)
  holds: list[tuple[int, int]] = field(default_factory=list)


def parse_batch(lines: list[str]) -> list[TraceEvent]:
  events: list[TraceEvent] = []
  seen_begin = False
  for raw in lines:
    line = raw.strip()
    if BEGIN_RE.search(line):
      seen_begin = True
      events = []
      continue
    if not seen_begin:
      continue
    m = EVENT_RE.search(line)
    if m:
      events.append(
          TraceEvent(
              seq=int(m.group("seq")),
              time=int(m.group("time")),
              cpu=int(m.group("cpu")),
              pid=int(m.group("pid")),
              kind=m.group("kind"),
              hold=int(m.group("hold")),
              lock=m.group("lock"),
              name=m.group("name"),
          )
      )
      continue
    if END_RE.search(line):
      return events
  return []


def collect_events(stream_batches: list[list[TraceEvent]]) -> list[TraceEvent]:
  events: list[TraceEvent] = []
  for batch in stream_batches:
    events.extend(batch)
  events.sort(key=lambda e: (e.time, e.seq))
  return events


def build_tracks(events: list[TraceEvent], window_events: int) -> tuple[list[ProcTrack], int, int, str]:
  if not events:
    return [], 0, 0, "vizlock"

  window = events[-window_events:] if len(events) > window_events else events
  window_start = window[0].time
  window_end = window[-1].time
  if window_end <= window_start:
    window_end = window_start + 1

  waits_by_pid: dict[int, list[tuple[int, int]]] = {}
  holds_by_pid: dict[int, list[tuple[int, int]]] = {}
  name_by_pid: dict[int, str] = {}
  lock_name = window[0].lock
  pending_try: dict[int, int] = {}
  pending_acq: dict[int, int] = {}

  for event in events:
    if event.lock:
      lock_name = event.lock
    if event.pid < 0 or event.kind not in {"try", "acq", "rel"}:
      continue
    if event.name in EXCLUDED_NAMES:
      continue
    name_by_pid[event.pid] = event.name
    if event.kind == "try":
      pending_try[event.pid] = event.time
      continue
    if event.kind == "acq":
      start = pending_try.pop(event.pid, None)
      if start is not None and event.time > start:
        waits_by_pid.setdefault(event.pid, []).append((start, event.time))
      pending_acq[event.pid] = event.time
      continue
    if event.kind == "rel":
      start = pending_acq.pop(event.pid, None)
      if start is not None and event.time > start:
        holds_by_pid.setdefault(event.pid, []).append((start, event.time))

  for pid, start in list(pending_try.items()):
    if window_end > start:
      waits_by_pid.setdefault(pid, []).append((start, window_end))
  for pid, start in list(pending_acq.items()):
    if window_end > start:
      holds_by_pid.setdefault(pid, []).append((start, window_end))

  tracks: list[ProcTrack] = []
  for pid in sorted(set(waits_by_pid) | set(holds_by_pid)):
    waits = [
        (max(start, window_start), min(end, window_end))
        for start, end in waits_by_pid.get(pid, [])
        if not (end <= window_start or start >= window_end)
    ]
    holds = [
        (max(start, window_start), min(end, window_end))
        for start, end in holds_by_pid.get(pid, [])
        if not (end <= window_start or start >= window_end)
    ]
    if not waits and not holds:
      continue
    base = color_for_pid(pid)
    tracks.append(
        ProcTrack(
            pid=pid,
            name=name_by_pid.get(pid, f"pid{pid}"),
            color=shade(base, helper_tint(name_by_pid.get(pid, ""))),
            waits=waits,
            holds=holds,
        )
    )

  tracks.sort(key=lambda t: (t.waits[0][0] if t.waits else t.holds[0][0], t.pid))
  return tracks, window_start, window_end, lock_name


def time_label(raw_delta: int) -> str:
  if raw_delta < 1000:
    return str(raw_delta)
  if raw_delta < 1000000:
    return f"{raw_delta // 1000}k"
  return f"{raw_delta // 1000000}M"


def render_svg(events: list[TraceEvent], output_path: str, window_events: int) -> None:
  tracks, window_start, window_end, lock_name = build_tracks(events, window_events)
  left_margin = 20
  top_margin = 112
  label_w = 260
  row_h = 34
  width = 1600
  axis_h = 28
  height = top_margin + max(1, len(tracks)) * row_h + axis_h + 60
  chart_x = left_margin + label_w
  chart_y = top_margin
  chart_w = width - chart_x - left_margin
  span = max(1, window_end - window_start)

  lines = [
      '<?xml version="1.0" encoding="UTF-8"?>',
      f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
      '<rect width="100%" height="100%" fill="#f7f7f3"/>',
      f'<text x="{left_margin}" y="30" font-family="monospace" font-size="24" fill="#111">xv6 lock contention timeline</text>',
      f'<text x="{left_margin}" y="54" font-family="monospace" font-size="14" fill="#444">light bars show waiting time; solid bars show time spent inside the critical section</text>',
      f'<text x="{left_margin}" y="74" font-family="monospace" font-size="12" fill="#555">lock {escape(lock_name)}; window size: last {min(window_events, len(events))} event(s), span {time_label(span)}</text>',
      f'<rect x="{left_margin}" y="86" width="{width - 2 * left_margin}" height="10" rx="4" fill="#d9dde1"/>',
      f'<text x="{left_margin}" y="84" font-family="monospace" font-size="12" fill="#555">window start {time_label(window_start)} end {time_label(window_end)}</text>',
  ]

  for frac in range(0, 11):
    x = chart_x + int(chart_w * frac / 10)
    delta = int(span * frac / 10)
    lines.append(f'<line x1="{x}" y1="{chart_y - 8}" x2="{x}" y2="{height - 28}" stroke="#c9c9bf" stroke-width="1"/>')
    lines.append(f'<text x="{x + 2}" y="{chart_y - 12}" font-family="monospace" font-size="10" fill="#555">{escape(time_label(delta))}</text>')

  if not tracks:
    lines.append(f'<text x="{left_margin}" y="{top_margin + 40}" font-family="monospace" font-size="14" fill="#444">no lock events captured</text>')
  else:
    for row, track in enumerate(tracks):
      y = chart_y + row * row_h
      wait_total = sum(end - start for start, end in track.waits)
      hold_total = sum(end - start for start, end in track.holds)
      label = f"PID {track.pid} {track.name}"
      lines.extend([
          f'<rect x="{left_margin}" y="{y}" width="{label_w - 12}" height="{row_h - 4}" rx="8" fill="#ffffff" stroke="#d9d9d0" stroke-width="1"/>',
          f'<rect x="{left_margin + 8}" y="{y + 9}" width="10" height="10" rx="2" fill="{track.color}" stroke="#333" stroke-width="0.6"/>',
          f'<text x="{left_margin + 24}" y="{y + 16}" font-family="monospace" font-size="12" fill="#111">{escape(label)}</text>',
          f'<text x="{left_margin + 24}" y="{y + 29}" font-family="monospace" font-size="10" fill="#555">wait {time_label(wait_total)} hold {time_label(hold_total)}</text>',
      ])

      for start, end in track.waits:
        x1 = chart_x + int((start - window_start) * chart_w / span)
        x2 = chart_x + int((end - window_start) * chart_w / span)
        w = max(3, x2 - x1)
        lines.append(f'<rect x="{x1}" y="{y + 7}" width="{w}" height="{row_h - 14}" rx="5" fill="{track.color}" fill-opacity="0.28" stroke="{track.color}" stroke-width="0.8" stroke-dasharray="4 2"/>')
      for start, end in track.holds:
        x1 = chart_x + int((start - window_start) * chart_w / span)
        x2 = chart_x + int((end - window_start) * chart_w / span)
        w = max(3, x2 - x1)
        lines.append(f'<rect x="{x1}" y="{y + 7}" width="{w}" height="{row_h - 14}" rx="5" fill="{track.color}" fill-opacity="0.92" stroke="#333" stroke-width="0.8"/>')

  lines.extend([
      f'<text x="{left_margin}" y="{height - 8}" font-family="monospace" font-size="11" fill="#555">dashed bars show time spent waiting for the lock; solid bars show the critical section itself</text>',
      "</svg>",
  ])

  with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))


def render_png(events: list[TraceEvent], output_path: str, window_events: int):
  tracks, window_start, window_end, lock_name = build_tracks(events, window_events)
  left_margin = 20
  top_margin = 112
  label_w = 260
  row_h = 34
  width = 1600
  height = top_margin + max(1, len(tracks)) * row_h + 60
  chart_x = left_margin + label_w
  chart_y = top_margin
  chart_w = width - chart_x - left_margin
  span = max(1, window_end - window_start)

  img = Image.new("RGB", (width, height), "#f7f7f3")
  draw = ImageDraw.Draw(img)
  font_title = ImageFont.load_default()
  font_body = ImageFont.load_default()

  draw.text((left_margin, 18), "xv6 lock contention timeline", fill="#111", font=font_title)
  draw.text((left_margin, 42), "light bars show waiting time; solid bars show time spent inside the critical section", fill="#444", font=font_body)
  draw.text((left_margin, 62), f"lock {lock_name}; window size: last {min(window_events, len(events))} event(s), span {time_label(span)}", fill="#555", font=font_body)
  draw.rounded_rectangle((left_margin, 86, width - left_margin, 96), radius=4, fill="#d9dde1")
  draw.text((left_margin, 80), f"window start {time_label(window_start)} end {time_label(window_end)}", fill="#555", font=font_body)

  for frac in range(0, 11):
    x = chart_x + int(chart_w * frac / 10)
    delta = int(span * frac / 10)
    draw.line((x, chart_y - 8, x, height - 28), fill="#c9c9bf", width=1)
    draw.text((x + 2, chart_y - 18), time_label(delta), fill="#555", font=font_body)

  if not tracks:
    draw.text((left_margin, top_margin + 40), "no lock events captured", fill="#444", font=font_body)
  else:
    for row, track in enumerate(tracks):
      y = chart_y + row * row_h
      wait_total = sum(end - start for start, end in track.waits)
      hold_total = sum(end - start for start, end in track.holds)
      label = f"PID {track.pid} {track.name}"
      draw.rounded_rectangle((left_margin, y, left_margin + label_w - 12, y + row_h - 4), radius=8, fill="#ffffff", outline="#d9d9d0", width=1)
      draw.rounded_rectangle((left_margin + 8, y + 9, left_margin + 18, y + 19), radius=2, fill=track.color, outline="#333", width=1)
      draw.text((left_margin + 24, y + 4), label, fill="#111", font=font_body)
      draw.text((left_margin + 24, y + 17), f"wait {time_label(wait_total)} hold {time_label(hold_total)}", fill="#555", font=font_body)
      for start, end in track.waits:
        x1 = chart_x + int((start - window_start) * chart_w / span)
        x2 = chart_x + int((end - window_start) * chart_w / span)
        w = max(3, x2 - x1)
        draw.rounded_rectangle((x1, y + 7, x1 + w, y + row_h - 11), radius=5, fill=shade(track.color, 0.28), outline=track.color, width=1)
      for start, end in track.holds:
        x1 = chart_x + int((start - window_start) * chart_w / span)
        x2 = chart_x + int((end - window_start) * chart_w / span)
        w = max(3, x2 - x1)
        draw.rounded_rectangle((x1, y + 7, x1 + w, y + row_h - 11), radius=5, fill=track.color, outline="#333", width=1)

  draw.text((left_margin, height - 18), "dashed bars show waiting; solid bars show the critical section", fill="#555", font=font_body)
  img.save(output_path)
  return img


def main() -> int:
  parser = argparse.ArgumentParser(description="Render an xv6 lock contention timeline")
  parser.add_argument("--output", default="lockviz.svg", help="output SVG path")
  parser.add_argument("--runtime", type=int, default=6, help="seconds to collect trace batches")
  parser.add_argument("--poll", type=int, default=1, help="locktrace interval in ticks")
  parser.add_argument("--events", type=int, default=120, help="number of recent events to render")
  parser.add_argument("--window", action="store_true", help="show a live desktop window")
  parser.add_argument("--cpus", type=int, default=2, help="number of QEMU CPUs to use")
  parser.add_argument("--waves", type=int, default=5, help="lockwork waves")
  parser.add_argument("--burst", type=int, default=3, help="lockwork children per wave")
  parser.add_argument("--hold", type=int, default=120000, help="lockwork critical-section duration")
  parser.add_argument("--gap", type=int, default=40000, help="lockwork pause between attempts")
  args = parser.parse_args()

  proc = subprocess.Popen(
      ["make", "qemu", f"CPUS={args.cpus}"],
      stdin=subprocess.PIPE,
      stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,
      text=True,
      bufsize=1,
  )

  try:
    png_output = os.path.splitext(args.output)[0] + ".png"
    window_w = 1600
    window_h = 740
    wait_for_prompt(proc)
    proc.stdin.write(f"locktrace {args.poll} &\n")
    proc.stdin.write(f"lockwork {args.waves} {args.burst} {args.hold} {args.gap} &\n")
    proc.stdin.flush()

    batches: queue.Queue[list[TraceEvent]] = queue.Queue()
    stop = threading.Event()

    def reader():
      buffer: list[str] = []
      while not stop.is_set():
        line = proc.stdout.readline()
        if not line:
          break
        buffer.append(line)
        if END_RE.search(line):
          batch = parse_batch(buffer)
          buffer = []
          if batch:
            batches.put(batch)

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()

    events: list[TraceEvent] = []

    if args.window:
      try:
        root = Tk()
      except TclError:
        sys.stderr.write("no display available; falling back to file output\n")
        sys.stderr.flush()
        args.window = False
      else:
        root.title("xv6 lock contention timeline")
        root.geometry(f"{window_w}x{window_h}")
        root.resizable(False, False)
        canvas = Canvas(root, width=window_w, height=window_h, highlightthickness=0, bg="#f7f7f3")
        canvas.pack(fill="both", expand=True)
        image_id = None
        photo = None

        def pump():
          nonlocal image_id, photo
          drained = False
          while True:
            try:
              batch = batches.get_nowait()
            except queue.Empty:
              break
            events.extend(batch)
            drained = True
          if drained and events:
            render_svg(events, args.output, args.events)
            img = render_png(events, png_output, args.events)
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
            sys.stderr.write(f"wrote {args.output} and {png_output} with {len(events)} event(s)\n")
            sys.stderr.flush()
          if proc.poll() is None and not stop.is_set():
            root.after(120, pump)
          else:
            root.after(120, pump)

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
          batch = batches.get(timeout=0.5)
        except queue.Empty:
          continue
        events.extend(batch)
        render_svg(events, args.output, args.events)
        sys.stderr.write(f"wrote {args.output} with {len(events)} event(s)\n")
        sys.stderr.flush()

    if events:
      if not args.window:
        render_svg(events, args.output, args.events)
      return 0
    sys.stderr.write("no complete trace captured\n")
    return 1
  finally:
    stop.set()
    proc.terminate()


if __name__ == "__main__":
  raise SystemExit(main())
