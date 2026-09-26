#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Inspect closed DOS FAT12 results independently of the input allocator.

Free-cluster payloads and deleted directory records may retain old bytes.
Allocated chains, live directory entries and all FAT copies must agree.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/m05"))
from common import decode_dos_name, derive_layout  # noqa: E402
from build_media import build_boot_record  # noqa: E402
from inspect_media import parse_d88  # noqa: E402


def inspect(image: bytes, spec: dict) -> tuple[dict, dict[str, bytes]]:
    layout = derive_layout(spec)
    _, raw = parse_d88(image, spec, layout)
    geometry, fs = spec["geometry"], spec["filesystem"]
    bps, cluster_bytes = geometry["bytes_per_sector"], geometry["bytes_per_sector"] * fs["sectors_per_cluster"]
    if raw[11:36] != build_boot_record(spec)[11:36]:
        raise ValueError("BPB disagrees with the supported geometry")
    fat_start, fat_size = fs["reserved_sectors"] * bps, fs["sectors_per_fat"] * bps
    fat = raw[fat_start:fat_start + fat_size]
    for copy in range(fs["fat_count"]):
        if raw[fat_start + copy * fat_size:fat_start + (copy + 1) * fat_size] != fat:
            raise ValueError("FAT copies disagree")

    def value(cluster):
        # Deliberately independent of the producer's set/get entry helpers.
        offset = cluster * 3 // 2
        packed = int.from_bytes(fat[offset:offset + 2], "little")
        return (packed >> (4 if cluster & 1 else 0)) & 0xFFF

    if value(0) != 0xF00 | fs["media_descriptor"] or value(1) != 0xFFF:
        raise ValueError("reserved FAT entries are malformed")
    maximum = layout["data_clusters"] + 1
    if fat[layout["fat_bytes_required"]:] != bytes(fat_size - layout["fat_bytes_required"]):
        raise ValueError("unused FAT bytes are nonzero")
    if (maximum + 1) & 1 and fat[layout["fat_bytes_required"] - 1] & 0xF0:
        raise ValueError("unused FAT nibble is nonzero")
    owners, files, records, directories = {}, {}, {}, {}
    volume_label = None

    def read_chain(first, owner):
        chain, data = [], bytearray()
        cluster = first
        while True:
            if not 2 <= cluster <= maximum:
                raise ValueError("chain is outside the data area")
            if cluster in owners:
                raise ValueError("cyclic or cross-linked chain")
            owners[cluster] = owner
            chain.append(cluster)
            offset = layout["first_data_sector"] * bps + (cluster - 2) * cluster_bytes
            data.extend(raw[offset:offset + cluster_bytes])
            cluster = value(cluster)
            if 0xFF8 <= cluster <= 0xFFF:
                return chain, bytes(data)

    root_start = fat_start + fs["fat_count"] * fat_size
    root = raw[root_start:root_start + layout["root_directory_sectors"] * bps]
    pending = [("", 0, 0, root)]
    while pending:
        path, current, parent, data = pending.pop()
        names, dots = set(), set()
        for offset in range(0, len(data), 32):
            entry = data[offset:offset + 32]
            if not entry[0]:
                break
            if entry[0] == 0xE5:
                continue
            attributes = entry[11]
            if attributes == 0x0F or attributes & 0xC0 or entry[20:22] != b"\0\0":
                raise ValueError("unsupported live directory entry")
            first, size = struct.unpack_from("<HI", entry, 26)
            if entry[:11] in (b".          ", b"..         "):
                dot = entry[:11].rstrip().decode("ascii")
                if not path or dot in dots or attributes != 0x10 or size or first != (current if dot == "." else parent):
                    raise ValueError("invalid directory self/parent link")
                dots.add(dot)
                continue
            if attributes & 8:
                if (path or attributes & 0x10 or first or size or volume_label is not None
                        or any(value < 32 or value > 126 for value in entry[:11])):
                    raise ValueError("invalid volume-label entry")
                volume_label = entry[:11].decode("ascii").rstrip()
                continue
            name = decode_dos_name(entry[:11])
            if name in names:
                raise ValueError("duplicate live filename")
            names.add(name)
            full_name = path + name
            if attributes & 0x10:
                if size:
                    raise ValueError("directory has a nonzero file length")
                chain, contents = read_chain(first, full_name)
                directories[full_name] = {"clusters": chain}
                pending.append((full_name + "/", first, current, contents))
                continue
            if not size and not first:
                chain, contents = [], b""
            else:
                chain, contents = read_chain(first, full_name)
            if len(chain) != (size + cluster_bytes - 1) // cluster_bytes:
                raise ValueError("file length and chain disagree")
            files[full_name] = contents[:size]
            records[full_name] = {"size": size, "clusters": chain, "attributes": attributes,
                                  "sha256": hashlib.sha256(contents[:size]).hexdigest()}
        if path and dots != {".", ".."}:
            raise ValueError("directory self/parent links are missing")
    free = []
    for cluster in range(2, maximum + 1):
        if cluster not in owners:
            if value(cluster):
                raise ValueError("orphaned allocation or unqualified bad cluster")
            free.append(cluster)
    return {"files": records, "directories": directories, "free_clusters": free,
            "fat_copies_equal": True, "allocated_clusters": len(owners),
            "volume_label": volume_label,
            "d88_sha256": hashlib.sha256(image).hexdigest()}, files
