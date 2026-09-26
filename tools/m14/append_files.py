#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Append original guest fixtures without reallocating an existing boot image.

This prepares disposable inputs only. It is never a substitute for DOS writes.
The accepted input is a canonical flat FAT12 root with regular files; reject
other layouts instead of guessing how to preserve their allocation semantics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/m05"))
from common import derive_layout, encode_dos_name  # noqa: E402
from build_media import build_boot_record, set_fat12_entry  # noqa: E402
from inspect_media import get_fat12_entry, parse_d88, parse_root_directory  # noqa: E402


def append_files(original: bytes, additions: dict[str, bytes], spec: dict) -> tuple[bytes, dict]:
    layout = derive_layout(spec)
    _, source = parse_d88(original, spec, layout)
    fs, geometry = spec["filesystem"], spec["geometry"]
    bps = geometry["bytes_per_sector"]
    cluster_bytes = bps * fs["sectors_per_cluster"]
    # Validate the actual BPB, allowing an existing executable boot sector.
    if source[11:36] != build_boot_record(spec)[11:36]:
        raise ValueError("input BPB differs from the supported geometry")
    fat_start = fs["reserved_sectors"] * bps
    fat_size = fs["sectors_per_fat"] * bps
    fat = source[fat_start:fat_start + fat_size]
    for copy in range(fs["fat_count"]):
        if source[fat_start + copy * fat_size:fat_start + (copy + 1) * fat_size] != fat:
            raise ValueError("input FAT copies disagree")
    if get_fat12_entry(fat, 0) != 0xF00 | fs["media_descriptor"] or get_fat12_entry(fat, 1) != 0xFFF:
        raise ValueError("input FAT reserved entries are invalid")
    if fat[layout["fat_bytes_required"]:] != bytes(fat_size - layout["fat_bytes_required"]):
        raise ValueError("input has nonzero unused FAT bytes")
    if (layout["data_clusters"] + 2) & 1 and fat[layout["fat_bytes_required"] - 1] & 0xF0:
        raise ValueError("input has a nonzero unused FAT nibble")
    root_start = fat_start + fs["fat_count"] * fat_size
    root_size = layout["root_directory_sectors"] * bps
    entries = parse_root_directory(source[root_start:root_start + root_size])
    existing = {entry["dos_name"] for entry in entries}
    if not additions or existing.intersection(additions):
        raise ValueError("additions are empty or replace an existing file")
    if len(entries) + len(additions) >= fs["root_entries"]:
        raise ValueError("insufficient root slots including the end marker")
    for name, content in additions.items():
        encode_dos_name(name)
        if not isinstance(content, bytes) or not content:
            raise ValueError("fixture additions must be nonempty byte payloads")
    used = set()
    for entry in entries:
        cluster, chain = entry["first_cluster"], []
        if not entry["size"] and not cluster:
            continue
        while True:
            if not 2 <= cluster < layout["data_clusters"] + 2 or cluster in used:
                raise ValueError("input chain is invalid, cyclic or cross-linked")
            used.add(cluster)
            chain.append(cluster)
            cluster = get_fat12_entry(fat, cluster)
            if 0xFF8 <= cluster <= 0xFFF:
                break
        if len(chain) != (entry["size"] + cluster_bytes - 1) // cluster_bytes:
            raise ValueError("input file length and chain disagree")
    free = []
    for cluster in range(2, layout["data_clusters"] + 2):
        value = get_fat12_entry(fat, cluster)
        if cluster not in used:
            if value:
                raise ValueError("input has an orphaned or reserved allocation")
            free.append(cluster)
    needed = sum((len(content) + cluster_bytes - 1) // cluster_bytes for content in additions.values())
    if needed > len(free):
        raise ValueError("insufficient free clusters")

    raw, new_fat, allocations = bytearray(source), bytearray(fat), {}
    cursor = 0
    for index, (name, content) in enumerate(sorted(additions.items())):
        count = (len(content) + cluster_bytes - 1) // cluster_bytes
        chain = free[cursor:cursor + count]
        cursor += count
        allocations[name] = chain
        for position, cluster in enumerate(chain):
            set_fat12_entry(new_fat, cluster, chain[position + 1] if position + 1 < count else 0xFFF)
            offset = layout["first_data_sector"] * bps + (cluster - 2) * cluster_bytes
            raw[offset:offset + cluster_bytes] = content[position * cluster_bytes:(position + 1) * cluster_bytes].ljust(cluster_bytes, b"\0")
        record = bytearray(32)
        record[:11] = encode_dos_name(name)
        record[11] = 0x20
        if entries:
            record[14:26] = source[root_start + 14:root_start + 26]
        struct.pack_into("<HI", record, 26, chain[0], len(content))
        offset = root_start + (len(entries) + index) * 32
        raw[offset:offset + 32] = record
    for copy in range(fs["fat_count"]):
        offset = fat_start + copy * fat_size
        raw[offset:offset + fat_size] = new_fat
    # Do not rebuild D88 metadata, boot code, existing root entries or files.
    output = bytearray(original)
    lba = 0
    for track in range(geometry["cylinders"] * geometry["heads"]):
        offset = struct.unpack_from("<I", original, 0x20 + track * 4)[0]
        for _ in range(geometry["sectors_per_track"]):
            size = struct.unpack_from("<H", original, offset + 14)[0]
            if size != bps:
                raise ValueError("D88 sector extent changed during preparation")
            output[offset + 16:offset + 16 + bps] = raw[lba * bps:(lba + 1) * bps]
            lba += 1
            offset += 16 + bps
    _, roundtrip = parse_d88(bytes(output), spec, layout)
    if roundtrip != raw:
        raise ValueError("prepared D88 does not round-trip")
    record = {"scope": "disposable input preparation, not DOS write evidence",
              "before_sha256": hashlib.sha256(original).hexdigest(),
              "after_sha256": hashlib.sha256(output).hexdigest(),
              "allocations": allocations,
              "payloads": {name: {"size": len(content), "sha256": hashlib.sha256(content).hexdigest()}
                           for name, content in sorted(additions.items())}}
    return bytes(output), record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--file", action="append", required=True, metavar="DOSNAME=PATH")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    original = args.base.read_bytes()
    if hashlib.sha256(original).hexdigest() != args.expected_sha256:
        raise ValueError("input identity mismatch")
    output = args.output.resolve()
    if output.suffix.lower() != ".d88":
        raise ValueError("output must have a D88 suffix")
    manifest = output.with_suffix(".json")
    for path in (output, manifest):
        path.relative_to(ROOT)
        if path.exists() or path.is_symlink():
            raise ValueError("output already exists")
        ignored = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", "--", str(path)])
        if ignored.returncode != 0:
            raise ValueError("output must be persistently Git-excluded")
    additions = {}
    for item in args.file:
        name, path = item.split("=", 1)
        if name in additions:
            raise ValueError("duplicate addition")
        additions[name] = Path(path).read_bytes()
    spec = json.loads((ROOT / "config/m05/media.json").read_text())
    data, record = append_files(original, additions, spec)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        handle.write(data)
    with manifest.open("x") as handle:
        json.dump(record, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(record, sort_keys=True))


if __name__ == "__main__":
    main()
