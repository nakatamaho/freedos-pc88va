#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Independently compare an exclusive block probe's before/after D88 bytes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/m05"))
from common import ValidationError, derive_layout  # noqa: E402
from inspect_media import parse_d88  # noqa: E402


def cases(spec: dict) -> list[tuple[int, int]]:
    g = spec["geometry"]
    return [(0, 1), (g["sectors_per_track"] - 1, 2),
            (g["sectors_per_track"] * g["heads"] - 1, 2),
            (g["total_sectors"] - 1, 1)]


def pattern(lba: int, count: int, bps: int) -> bytes:
    return b"".join(struct.pack("<H", ((lba ^ 0xA55A) + i * 17) & 0xFFFF)
                    for i in range(count * bps // 2))


def check(before: bytes, after: bytes, spec: dict, restored: bool) -> dict:
    layout = derive_layout(spec)
    # The qualified parser checks track topology, CHRN, header fields and
    # exact payload lengths. It does not assume that the mutated BPB is valid.
    try:
        _, raw_before = parse_d88(before, spec, layout)
        _, raw_after = parse_d88(after, spec, layout)
    except ValidationError as error:
        raise ValueError(str(error)) from error
    if len(before) != len(after):
        raise ValueError("D88 length changed")
    g = spec["geometry"]
    bps = g["bytes_per_sector"]
    expected = bytearray(raw_before)
    targets = []
    for lba, count in cases(spec):
        targets.extend(range(lba, lba + count))
        if not restored:
            expected[lba*bps:(lba+count)*bps] = pattern(lba, count, bps)
    if len(targets) != len(set(targets)):
        raise ValueError("probe cases overlap")
    changed = [i for i in range(g["total_sectors"])
               if raw_before[i*bps:(i+1)*bps] != raw_after[i*bps:(i+1)*bps]]
    if raw_after != expected:
        wrong = [i for i in range(g["total_sectors"])
                 if raw_after[i*bps:(i+1)*bps] != expected[i*bps:(i+1)*bps]]
        raise ValueError("unexpected sector contents: " + repr(wrong))
    # Normalize only sector payloads and compare everything else, including
    # the disk header, track offsets, protection and sector status fields.
    metadata_before = bytearray(before)
    metadata_after = bytearray(after)
    for track in range(g["cylinders"] * g["heads"]):
        offset = struct.unpack_from("<I", before, 0x20 + 4*track)[0]
        for _ in range(g["sectors_per_track"]):
            length = struct.unpack_from("<H", before, offset+14)[0]
            if length != bps:
                raise ValueError("unexpected sector size")
            metadata_before[offset+16:offset+16+bps] = bytes(bps)
            metadata_after[offset+16:offset+16+bps] = bytes(bps)
            offset += 16+bps
    if metadata_before != metadata_after:
        raise ValueError("D88 metadata changed")
    return {"check": "block-post-run-byte-comparison", "restored": restored,
            "before_sha256": hashlib.sha256(before).hexdigest(),
            "after_sha256": hashlib.sha256(after).hexdigest(),
            "target_lbas": targets, "changed_lbas": changed,
            "changed_bytes": sum(a != b for a, b in zip(before, after)),
            "metadata_unchanged": True}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--restored", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads((ROOT / "config/m05/media.json").read_text())
    result = check(args.before.read_bytes(), args.after.read_bytes(), spec, args.restored)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
