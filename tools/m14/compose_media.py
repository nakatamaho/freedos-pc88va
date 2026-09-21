#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Compose private M14 VA media from an exact base D88 and guest payloads.

The base image is an input, never modified in place.  Outputs are written to
an explicitly selected ignored directory and include a raw image, D88 image,
and a JSON binding record.  No private input path is embedded in the record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/m05"))
from build_media import build_boot_record, build_d88, encode_dos_name, set_fat12_entry  # noqa: E402
from common import derive_layout  # noqa: E402
from inspect_media import get_fat12_entry, inspect_raw, parse_d88, parse_root_directory  # noqa: E402


def identity(data: bytes) -> dict[str, object]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def extract(raw: bytes, entry: dict, fat: bytes, first_data: int, bps: int) -> bytes:
    result = bytearray()
    cluster = entry["first_cluster"]
    seen: set[int] = set()
    while cluster < 0xFF8:
        if cluster in seen:
            raise ValueError("base FAT chain loops")
        seen.add(cluster)
        start = (first_data + cluster - 2) * bps
        result.extend(raw[start:start + bps])
        cluster = get_fat12_entry(fat, cluster)
    return bytes(result[:entry["size"]])


def chain(start: int, size: int, bps: int) -> list[int]:
    count = max(1, (size + bps - 1) // bps)
    return list(range(start, start + count))


def compose(args: argparse.Namespace) -> dict:
    spec = json.loads((ROOT / "config/m05/media.json").read_text(encoding="utf-8"))
    derived = derive_layout(spec)
    bps = spec["geometry"]["bytes_per_sector"]
    fs = spec["filesystem"]
    summary, raw_base = parse_d88(args.base.read_bytes(), spec, derived)
    fat_start = fs["reserved_sectors"] * bps
    fat_size = fs["sectors_per_fat"] * bps
    root_start = (fs["reserved_sectors"] + fs["fat_count"] * fs["sectors_per_fat"]) * bps
    root_size = derived["root_directory_sectors"] * bps
    root_base = raw_base[root_start:root_start + root_size]
    entries = parse_root_directory(root_base)
    fat = raw_base[fat_start:fat_start + fat_size]
    payloads: dict[str, bytes] = {}
    for entry in entries:
        name = entry["dos_name"]
        payloads[name] = {
            "KERNEL.SYS": args.kernel.read_bytes(),
            "LOADER.BIN": args.stage2.read_bytes(),
        }.get(name, extract(raw_base, entry, fat, derived["first_data_sector"], bps))

    marker_name = ("MEDIAA.TXT" if args.marker == "A" else "MEDIAB.TXT")
    payloads[marker_name] = ("M14-MEDIA-" + args.marker + "\r\n").encode("ascii")
    payloads["M14FILE.COM"] = args.file_probe.read_bytes()
    payloads["M14FULL.COM"] = args.full_probe.read_bytes()

    assignments = {
        "KERNEL.SYS": chain(2, len(payloads["KERNEL.SYS"]), bps),
        "COMMAND.COM": chain(62, len(payloads["COMMAND.COM"]), bps),
        "COUNTRY.SYS": chain(143, len(payloads["COUNTRY.SYS"]), bps),
        "COMDATA.TXT": [185],
        "TYPEA.TXT": [186],
        "TYPEB.TXT": [187],
        "LOADER.BIN": chain(188, len(payloads["LOADER.BIN"]), bps),
        "COMPROBE.COM": [194],
        "MZPROBE.EXE": [195],
        "M14FILE.COM": chain(196, len(payloads["M14FILE.COM"]), bps),
        "M14FULL.COM": chain(204, len(payloads["M14FULL.COM"]), bps),
        marker_name: [220],
        "BIGFRAG.BIN": chain(300, len(payloads["BIGFRAG.BIN"]), bps),
    }
    names = {entry["dos_name"] for entry in entries}
    names.update(("M14FILE.COM", "M14FULL.COM", marker_name))
    if set(payloads) != names:
        raise ValueError("base root payload set differs from the M14 allocation contract")
    if any(max(values) >= derived["data_clusters"] + 2 for values in assignments.values()):
        raise ValueError("M14 allocation exceeds the FAT12 data area")
    used: set[int] = set()
    for name, values in assignments.items():
        if name not in payloads or not values or used.intersection(values):
            raise ValueError("M14 allocation is missing, empty, or cross-linked")
        used.update(values)
        if len(values) * bps < len(payloads[name]):
            raise ValueError("M14 allocation is too short for " + name)

    image = bytearray(raw_base)
    image[:bps] = args.stage1.read_bytes()
    if len(args.stage1.read_bytes()) != bps:
        raise ValueError("stage1 is not exactly one logical sector")
    image[3:62] = raw_base[3:62]
    image[510:512] = b"\x55\xaa"
    image[1022:1024] = b"\x55\xaa"
    image[derived["first_data_sector"] * bps:] = bytes(len(image) - derived["first_data_sector"] * bps)

    new_fat = bytearray(fat_size)
    set_fat12_entry(new_fat, 0, 0xF00 | fs["media_descriptor"])
    set_fat12_entry(new_fat, 1, 0xFFF)
    for name, values in assignments.items():
        data = payloads[name]
        for index, cluster in enumerate(values):
            set_fat12_entry(new_fat, cluster, values[index + 1] if index + 1 < len(values) else 0xFFF)
            start = (derived["first_data_sector"] + cluster - 2) * bps
            chunk = data[index * bps:(index + 1) * bps]
            image[start:start + len(chunk)] = chunk
    for copy in range(fs["fat_count"]):
        start = (fs["reserved_sectors"] + copy * fs["sectors_per_fat"]) * bps
        image[start:start + fat_size] = new_fat

    root = bytearray(root_base)
    for index, entry in enumerate(entries):
        name = entry["dos_name"]
        record = bytearray(root[index * 32:(index + 1) * 32])
        record[26:28] = assignments[name][0].to_bytes(2, "little")
        record[28:32] = len(payloads[name]).to_bytes(4, "little")
        root[index * 32:(index + 1) * 32] = record
    for name in ("M14FILE.COM", "M14FULL.COM", marker_name):
        index = next(i for i in range(len(root) // 32) if root[i * 32] == 0)
        record = bytearray(32)
        record[:11] = encode_dos_name(name)
        record[11] = 0x20
        # Preserve the base fixture's fixed UTC FAT timestamp; no ambient
        # wall-clock value is allowed into the disposable media record.
        record[14:26] = root[14:26]
        record[26:28] = assignments[name][0].to_bytes(2, "little")
        record[28:32] = len(payloads[name]).to_bytes(4, "little")
        root[index * 32:(index + 1) * 32] = record
    image[root_start:root_start + root_size] = root

    output_spec = json.loads(json.dumps(spec))
    if args.protected:
        output_spec["d88"]["write_protect"] = 0x10
    out = bytes(image)
    expected = [{"dos_name": name, "data": data, "size": len(data),
                 "sha256": hashlib.sha256(data).hexdigest(), "source_date_epoch": 1787814827}
                for name, data in payloads.items()]
    inspect_raw(build_boot_record(spec) + out[bps:], spec, derived, expected)
    d88 = build_d88(output_spec, out)
    args.output.mkdir(mode=0o700, parents=True, exist_ok=True)
    raw_path = args.output / (args.stem + ".img")
    d88_path = args.output / (args.stem + ".d88")
    raw_path.write_bytes(out)
    d88_path.write_bytes(d88)
    manifest = {
        "schema_version": 1, "milestone": "M14", "marker": args.marker,
        "protected": bool(args.protected), "base_d88": identity(args.base.read_bytes()),
        "raw": identity(out), "d88": identity(d88),
        "stage1": identity(args.stage1.read_bytes()), "stage2": identity(args.stage2.read_bytes()),
        "kernel": identity(args.kernel.read_bytes()),
        "allocations": {name: values for name, values in assignments.items()},
        "payloads": {name: identity(data) for name, data in payloads.items()},
    }
    (args.output / (args.stem + ".json")).write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--stage1", type=Path, required=True)
    parser.add_argument("--stage2", type=Path, required=True)
    parser.add_argument("--file-probe", type=Path, required=True)
    parser.add_argument("--full-probe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stem", required=True)
    parser.add_argument("--marker", choices=("A", "B"), required=True)
    parser.add_argument("--protected", action="store_true")
    args = parser.parse_args()
    manifest = compose(args)
    print(json.dumps({"d88": manifest["d88"], "raw": manifest["raw"], "marker": args.marker}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
