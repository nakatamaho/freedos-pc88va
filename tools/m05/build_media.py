#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Build the deterministic M05 FAT12 raw image and D88 container."""

from __future__ import annotations

import argparse
import os
import struct
import sys
from pathlib import Path

from common import (
    MILESTONE,
    SCHEMA_RELATIVE,
    SPEC_RELATIVE,
    ValidationError,
    accepted_artifacts,
    encode_dos_name,
    fat_datetime,
    file_identity,
    sha256_bytes,
    sha256_file,
    validate_chs_round_trip,
    validate_spec,
    write_canonical_json,
)


def set_fat12_entry(fat: bytearray, cluster: int, value: int) -> None:
    if not isinstance(cluster, int) or cluster < 0 or not isinstance(value, int) or not 0 <= value <= 0xFFF:
        raise ValidationError("invalid FAT12 entry request")
    offset = cluster + cluster // 2
    if offset + 1 >= len(fat):
        raise ValidationError("FAT12 entry exceeds the FAT byte region")
    if cluster & 1:
        fat[offset] = (fat[offset] & 0x0F) | ((value & 0x00F) << 4)
        fat[offset + 1] = (value >> 4) & 0xFF
    else:
        fat[offset] = value & 0xFF
        fat[offset + 1] = (fat[offset + 1] & 0xF0) | ((value >> 8) & 0x0F)


def build_boot_record(spec: dict) -> bytes:
    geometry = spec["geometry"]
    filesystem = spec["filesystem"]
    policy = spec["boot_record"]
    sector = bytearray(geometry["bytes_per_sector"])
    placeholder = bytes(policy["placeholder_code"])
    if placeholder != b"\xeb\xfe\x90":
        raise ValidationError("M05 placeholder must remain the documented self-loop")
    sector[0:3] = placeholder
    oem = policy["oem_name"].encode("ascii")
    if len(oem) != 8:
        raise ValidationError("OEM name must be exactly eight ASCII bytes")
    sector[3:11] = oem
    struct.pack_into("<H", sector, 11, geometry["bytes_per_sector"])
    sector[13] = filesystem["sectors_per_cluster"]
    struct.pack_into("<H", sector, 14, filesystem["reserved_sectors"])
    sector[16] = filesystem["fat_count"]
    struct.pack_into("<H", sector, 17, filesystem["root_entries"])
    struct.pack_into("<H", sector, 19, geometry["total_sectors"])
    sector[21] = filesystem["media_descriptor"]
    struct.pack_into("<H", sector, 22, filesystem["sectors_per_fat"])
    struct.pack_into("<H", sector, 24, geometry["sectors_per_track"])
    struct.pack_into("<H", sector, 26, geometry["heads"])
    struct.pack_into("<I", sector, 28, filesystem["hidden_sectors"])
    struct.pack_into("<I", sector, 32, 0)
    sector[36] = 0
    sector[37] = 0
    sector[38] = policy["extended_bpb_signature"]
    struct.pack_into("<I", sector, 39, spec["image"]["volume_serial"])
    label = spec["image"]["volume_label"].encode("ascii")
    if len(label) > 11:
        raise ValidationError("volume label exceeds 11 bytes")
    sector[43:54] = label.ljust(11, b" ")
    filesystem_type = policy["filesystem_type"].encode("ascii")
    if filesystem_type != b"FAT12":
        raise ValidationError("M05 filesystem type label changed")
    sector[54:62] = filesystem_type.ljust(8, b" ")
    if sector[510:512] == b"\x55\xaa" or sector[1022:1024] == b"\x55\xaa":
        raise ValidationError("M05 boot record contains an undeclared firmware signature")
    return bytes(sector)


def build_directory_entry(record: dict, first_cluster: int) -> tuple[bytes, dict]:
    entry = bytearray(32)
    entry[0:11] = encode_dos_name(record["dos_name"])
    entry[11] = 0x20
    fat_date, fat_time, rendered = fat_datetime(record["source_date_epoch"])
    struct.pack_into("<H", entry, 14, fat_time)
    struct.pack_into("<H", entry, 16, fat_date)
    struct.pack_into("<H", entry, 18, fat_date)
    struct.pack_into("<H", entry, 22, fat_time)
    struct.pack_into("<H", entry, 24, fat_date)
    struct.pack_into("<H", entry, 26, first_cluster)
    struct.pack_into("<I", entry, 28, record["size"])
    return bytes(entry), {"fat_date": fat_date, "fat_time": fat_time, "utc": rendered}


def build_raw_image(spec: dict, derived: dict, records: list[dict]) -> tuple[bytes, dict]:
    geometry = spec["geometry"]
    filesystem = spec["filesystem"]
    bps = geometry["bytes_per_sector"]
    cluster_bytes = bps * filesystem["sectors_per_cluster"]
    image = bytearray(derived["total_bytes"])
    boot = build_boot_record(spec)
    image[0:bps] = boot
    fat = bytearray(derived["fat_capacity_bytes"])
    set_fat12_entry(fat, 0, 0xF00 | filesystem["media_descriptor"])
    set_fat12_entry(fat, 1, 0xFFF)
    root = bytearray(derived["root_directory_sectors"] * bps)
    next_cluster = 2
    allocations = []
    names = set()
    for index, record in enumerate(records):
        name = record["dos_name"]
        if name in names:
            raise ValidationError(f"duplicate DOS filename: {name}")
        names.add(name)
        data = record["source_path"].read_bytes() if "source_path" in record else record["data"]
        if len(data) != record["size"] or sha256_bytes(data) != record["sha256"]:
            raise ValidationError(f"payload bytes do not match declared identity: {name}")
        cluster_count = (len(data) + cluster_bytes - 1) // cluster_bytes
        chain = list(range(next_cluster, next_cluster + cluster_count))
        if not chain or chain[-1] > derived["data_clusters"] + 1:
            raise ValidationError(f"payload does not fit the M05 data area: {name}")
        for position, cluster in enumerate(chain):
            set_fat12_entry(fat, cluster, chain[position + 1] if position + 1 < len(chain) else 0xFFF)
            data_lba = derived["first_data_sector"] + (cluster - 2) * filesystem["sectors_per_cluster"]
            offset = data_lba * bps
            chunk = data[position * cluster_bytes:(position + 1) * cluster_bytes]
            image[offset:offset + len(chunk)] = chunk
        entry, timestamp = build_directory_entry(record, chain[0])
        root[index * 32:(index + 1) * 32] = entry
        allocations.append({
            "clusters": chain,
            "dos_name": name,
            "first_cluster": chain[0],
            "sha256": record["sha256"],
            "size": record["size"],
            "source_date_epoch": record["source_date_epoch"],
            "fat_timestamp": timestamp,
        })
        next_cluster = chain[-1] + 1
    fat1_lba = filesystem["reserved_sectors"]
    fat2_lba = fat1_lba + filesystem["sectors_per_fat"]
    root_lba = fat2_lba + filesystem["sectors_per_fat"]
    image[fat1_lba * bps:(fat1_lba + filesystem["sectors_per_fat"]) * bps] = fat
    image[fat2_lba * bps:(fat2_lba + filesystem["sectors_per_fat"]) * bps] = fat
    image[root_lba * bps:(root_lba + derived["root_directory_sectors"]) * bps] = root
    summary = {
        "allocations": allocations,
        "boot_record": {"sha256": sha256_bytes(boot), "size": len(boot)},
        "fat_1": {"sha256": sha256_bytes(fat), "size": len(fat)},
        "fat_2": {"sha256": sha256_bytes(fat), "size": len(fat)},
        "root_directory": {"sha256": sha256_bytes(root), "size": len(root)},
    }
    return bytes(image), summary


def build_d88(spec: dict, raw: bytes) -> bytes:
    geometry = spec["geometry"]
    d88 = spec["d88"]
    if len(raw) != geometry["total_bytes"]:
        raise ValidationError("raw image size does not match the D88 payload geometry")
    header = bytearray(d88["header_size"])
    disk_name = d88["disk_name"].encode("ascii")
    if len(disk_name) > 17:
        raise ValidationError("D88 disk name exceeds 17 bytes")
    header[:17] = disk_name.ljust(17, b"\x00")
    header[26] = d88["write_protect"]
    header[27] = d88["disk_type"]
    struct.pack_into("<I", header, 28, d88["declared_size"])
    track_size = geometry["sectors_per_track"] * (
        d88["sector_header_size"] + geometry["bytes_per_sector"]
    )
    for track in range(d88["populated_tracks"]):
        struct.pack_into("<I", header, 32 + track * 4, d88["header_size"] + track * track_size)
    output = bytearray(header)
    lba = 0
    for cylinder in range(geometry["cylinders"]):
        for head in range(geometry["heads"]):
            for sector_index in range(geometry["sectors_per_track"]):
                sector_id = geometry["physical_sector_id_base"] + sector_index
                sector_header = struct.pack(
                    "<BBBBHBBBB3sBH",
                    cylinder,
                    head,
                    sector_id,
                    d88["sector_size_code"],
                    geometry["sectors_per_track"],
                    d88["mfm_density_field"],
                    d88["deleted_data"],
                    d88["error_status"],
                    0,
                    b"\x00\x00\x00",
                    d88["rpm_field"],
                    geometry["bytes_per_sector"],
                )
                output.extend(sector_header)
                start = lba * geometry["bytes_per_sector"]
                output.extend(raw[start:start + geometry["bytes_per_sector"]])
                lba += 1
    if lba != geometry["total_sectors"] or len(output) != d88["declared_size"]:
        raise ValidationError("D88 construction did not consume the complete raw image")
    return bytes(output)


def serializable_record(record: dict) -> dict:
    return {
        "bundle_path": record["bundle_path"],
        "component_commit": record["component_commit"],
        "component_namespace": record["component_namespace"],
        "dos_name": record["dos_name"],
        "runtime_claim": record["runtime_claim"],
        "sha256": record["sha256"],
        "size": record["size"],
        "source_date_epoch": record["source_date_epoch"],
        "source_role": record["source_role"],
    }


def build_once(root: Path, output: Path) -> dict:
    spec, derived = validate_spec(root)
    validate_chs_round_trip(spec["geometry"])
    records = accepted_artifacts(root, spec)
    if output.exists():
        raise ValidationError(f"M05 output already exists: {output}")
    output.mkdir(parents=True, mode=0o755)
    raw, raw_summary = build_raw_image(spec, derived, records)
    d88 = build_d88(spec, raw)
    raw_path = output / spec["image"]["raw_filename"]
    d88_path = output / spec["image"]["d88_filename"]
    raw_path.write_bytes(raw)
    d88_path.write_bytes(d88)
    os.chmod(raw_path, 0o644)
    os.chmod(d88_path, 0o644)
    manifest = {
        "builder_identities": {
            "build_media.py": sha256_file(Path(__file__)),
            "common.py": sha256_file(Path(__file__).with_name("common.py")),
        },
        "claims": {
            "firmware_boot_accepted": False,
            "hardware_validated": False,
            "nec98_kernel_runs_on_pc88va": False,
            "pc88va_kernel_present": False,
            "vaeg_validated": False,
        },
        "consumed_identities": spec["consumed_identities"],
        "d88": {**file_identity(d88_path), "populated_tracks": spec["d88"]["populated_tracks"], "sector_count": derived["total_sectors"]},
        "derived_layout": derived,
        "format_provenance": spec["format_provenance"],
        "inputs": [serializable_record(record) for record in records],
        "milestone": MILESTONE,
        "raw": file_identity(raw_path),
        "regions": raw_summary,
        "schema_version": 1,
        "specification_sha256": sha256_file(root / SPEC_RELATIVE),
        "specification_schema_sha256": sha256_file(root / SCHEMA_RELATIVE),
        "unknowns": spec["unknowns"],
        "validation": {
            "chs_lba_round_trip": "pass",
            "derived_layout": "pass",
            "payload_input_identity": "pass",
        },
    }
    write_canonical_json(output / "build-manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    try:
        manifest = build_once(root, output)
    except (OSError, OverflowError, ValueError, ValidationError) as exc:
        print(f"M05 build failed: {exc}", file=sys.stderr)
        return 1
    print(f"M05 media built: raw={manifest['raw']['sha256']} d88={manifest['d88']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
