#!/usr/bin/env python3
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "build" / "web" / "assets" / "fs.img"
DEFAULT_OUTPUT = ROOT / "build" / "web" / "assets" / "fs"


def split_image(input_path, output_dir, block_kb):
    block_size = block_kb * 1024
    if block_size <= 0 or block_size & (block_size - 1):
        raise ValueError("block size must be a positive power of two")

    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    with input_path.open("rb") as src:
        while True:
            chunk = src.read(block_size)
            if not chunk:
                break
            if len(chunk) < block_size:
                chunk += b"\0" * (block_size - len(chunk))
            (output_dir / f"blk{count:09d}.bin").write_bytes(chunk)
            count += 1

    (output_dir / "blk.txt").write_text(
        "{\n"
        f"  block_size: {block_kb},\n"
        f"  n_block: {count},\n"
        "}\n",
        encoding="ascii",
    )
    return count


def main():
    parser = argparse.ArgumentParser(description="Stage fs.img for JSLinux/TinyEMU HTTP block loading.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--block-kb", type=int, default=256)
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(args.input)

    count = split_image(args.input, args.output, args.block_kb)
    print(f"wrote {count} blocks to {args.output}")


if __name__ == "__main__":
    main()
