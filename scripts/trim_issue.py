#!/usr/bin/env python3
"""Trim trailing white rows from a rendered long image.

Usage:
    python3 scripts/trim_issue.py input.png output.png [--padding 61]

Keeps every row containing non-white content (sum of RGB < 735), then adds
`padding` rows of white below it. Writes `output` (may equal `input`).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--padding", type=int, default=61, help="white rows kept below content (default 61)")
    args = parser.parse_args()

    image = Image.open(args.input).convert("RGB")
    arr = np.asarray(image).astype(np.int32)
    non_white = (arr[..., 0] + arr[..., 1] + arr[..., 2]) < 735
    rows = np.where(non_white.any(axis=1))[0]
    assert rows.size, "image is entirely white"
    height = min(int(rows.max()) + 1 + args.padding, image.height)
    image.crop((0, 0, image.width, height)).save(args.output)
    print(args.output, (image.width, height))


if __name__ == "__main__":
    main()
