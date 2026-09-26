#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Independently inspect M05 FAT12 raw and D88 images read-only."""

from __future__ import annotations

import argparse
import os
import struct
import sys
from pathlib import Path

from common import (
    MILESTONE,
    ValidationError,
    accepted_artifacts,
    decode_dos_name,
    fat_datetime,
    file_identity,
    sha256_bytes,
    sha256_file,
    validate_chs_round_trip,
    validate_spec,
    write_canonical_json,
)


def get_fat12_entry(fat: bytes, cluster: int) -> int:
    if not isinstance(cluster, int) or cluster < 0:
        raise ValidationError("invalid FAT12 cluster index")
    offset = cluster + cluster // 2
    if offset + 1 >= len(fat):
        raise ValidationError("FAT12 entry exceeds the FAT byte region")
    word = fat[offset] | (fat[offset + 1] << 8)
    return ((word >> 4) if cluster & 1 else word) & 0xFFF


def inspect_boot_record(boot: bytes, spec: dict) -> dict:
    geometry = spec["geometry"]
    filesystem = spec["filesystem"]
    policy = spec["boot_record"]
    if len(boot) != geometry["bytes_per_sector"]:
        raise ValidationError("boot record does not fill one physical sector")
    if boot[:3] != bytes(policy["placeholder_code"]):
        raise ValidationError("boot placeholder is not the documented fail-closed self-loop")
    if boot[3:11] != policy["oem_name"].encode("ascii"):
        raise ValidationError("boot OEM identity mismatch")
    observed = {
        "bytes_per_sector": struct.unpack_from("<H", boot, 11)[0],
        "fat_count": boot[16],
        "heads": struct.unpack_from("<H", boot, 26)[0],
        "hidden_sectors": struct.unpack_from("<I", boot, 28)[0],
        "media_descriptor": boot[21],
        "reserved_sectors": struct.unpack_from("<H", boot, 14)[0],
        "root_entries": struct.unpack_from("<H", boot, 17)[0],
        "sectors_per_cluster": boot[13],
        "sectors_per_fat": struct.unpack_from("<H", boot, 22)[0],
        "sectors_per_track": struct.unpack_from("<H", boot, 24)[0],
        "total_sectors": struct.unpack_from("<H", boot, 19)[0],
    }
    expected = {
        "bytes_per_sector": geometry["bytes_per_sector"],
        "fat_count": filesystem["fat_count"],
        "heads": geometry["heads"],
        "hidden_sectors": filesystem["hidden_sectors"],
        "media_descriptor": filesystem["media_descriptor"],
        "reserved_sectors": filesystem["reserved_sectors"],
        "root_entries": filesystem["root_entries"],
        "sectors_per_cluster": filesystem["sectors_per_cluster"],
        "sectors_per_fat": filesystem["sectors_per_fat"],
        "sectors_per_track": geometry["sectors_per_track"],
        "total_sectors": geometry["total_sectors"],
    }
    if observed != expected or struct.unpack_from("<I", boot, 32)[0] != 0:
        raise ValidationError("on-disk BPB does not match the M05 contract")
    if boot[36:39] != bytes((0, 0, policy["extended_bpb_signature"])):
        raise ValidationError("extended BPB marker mismatch")
    if struct.unpack_from("<I", boot, 39)[0] != spec["image"]["volume_serial"]:
        raise ValidationError("volume serial mismatch")
    if boot[43:54] != spec["image"]["volume_label"].encode("ascii").ljust(11, b" "):
        raise ValidationError("volume label mismatch")
    if boot[54:62] != b"FAT12   ":
        raise ValidationError("filesystem type label mismatch")
    if boot[510:512] == b"\x55\xaa" or boot[1022:1024] == b"\x55\xaa":
        raise ValidationError("undeclared boot signature is present at offset 510 or 1022")
    assigned = bytearray(len(boot))
    assigned[:62] = boot[:62]
    if boot[62:] != bytes(len(boot) - 62):
        raise ValidationError("unassigned boot-record bytes are not zero")
    return {"bpb": observed, "sha256": sha256_bytes(boot), "size": len(boot)}


def parse_root_directory(root: bytes) -> list[dict]:
    entries = []
    names = set()
    end_offset = None
    for offset in range(0, len(root), 32):
        entry = root[offset:offset + 32]
        if entry[0] == 0:
            end_offset = offset
            break
        if entry[0] == 0xE5 or entry[11] != 0x20:
            raise ValidationError("deleted or non-archive root entry is outside the M05 contract")
        name = decode_dos_name(entry[:11])
        if name in names:
            raise ValidationError(f"duplicate DOS 8.3 filename: {name}")
        names.add(name)
        if entry[12:14] != b"\x00\x00" or entry[20:22] != b"\x00\x00":
            raise ValidationError(f"noncanonical directory metadata: {name}")
        entries.append({
            "access_date": struct.unpack_from("<H", entry, 18)[0],
            "creation_date": struct.unpack_from("<H", entry, 16)[0],
            "creation_time": struct.unpack_from("<H", entry, 14)[0],
            "dos_name": name,
            "first_cluster": struct.unpack_from("<H", entry, 26)[0],
            "size": struct.unpack_from("<I", entry, 28)[0],
            "write_date": struct.unpack_from("<H", entry, 24)[0],
            "write_time": struct.unpack_from("<H", entry, 22)[0],
        })
    if end_offset is None:
        raise ValidationError("root directory has no canonical end marker")
    if root[end_offset:] != bytes(len(root) - end_offset):
        raise ValidationError("unused root directory bytes are not zero")
    return entries


def inspect_raw(raw: bytes, spec: dict, derived: dict, expected_records: list[dict]) -> tuple[dict, dict[str, bytes]]:
    geometry = spec["geometry"]
    filesystem = spec["filesystem"]
    bps = geometry["bytes_per_sector"]
    if len(raw) != derived["total_bytes"]:
        raise ValidationError("raw image size is not exactly the M05 logical capacity")
    boot = raw[:bps]
    boot_summary = inspect_boot_record(boot, spec)
    fat1_lba = filesystem["reserved_sectors"]
    fat2_lba = fat1_lba + filesystem["sectors_per_fat"]
    root_lba = fat2_lba + filesystem["sectors_per_fat"]
    fat_size = filesystem["sectors_per_fat"] * bps
    fat1 = raw[fat1_lba * bps:fat1_lba * bps + fat_size]
    fat2 = raw[fat2_lba * bps:fat2_lba * bps + fat_size]
    if fat1 != fat2:
        raise ValidationError("FAT copies are not byte-identical")
    if get_fat12_entry(fat1, 0) != 0xF00 | filesystem["media_descriptor"] or get_fat12_entry(fat1, 1) != 0xFFF:
        raise ValidationError("FAT12 reserved entries are malformed")
    if (derived["data_clusters"] + 2) & 1 and fat1[derived["fat_bytes_required"] - 1] & 0xF0:
        raise ValidationError("unused high nibble in the final FAT12 byte is nonzero")
    if fat1[derived["fat_bytes_required"]:] != bytes(fat_size - derived["fat_bytes_required"]):
        raise ValidationError("unused FAT bytes are not zero")
    root_size = derived["root_directory_sectors"] * bps
    root = raw[root_lba * bps:root_lba * bps + root_size]
    entries = parse_root_directory(root)
    expected_by_name = {item["dos_name"]: item for item in expected_records}
    if len(expected_by_name) != len(expected_records) or set(expected_by_name) != {item["dos_name"] for item in entries}:
        raise ValidationError("root directory payload set differs from the accepted M05 inputs")
    cluster_bytes = bps * filesystem["sectors_per_cluster"]
    max_cluster = derived["data_clusters"] + 1
    all_used = set()
    allocations = []
    extracted = {}
    for entry in entries:
        expected = expected_by_name[entry["dos_name"]]
        if entry["size"] != expected["size"]:
            raise ValidationError(f"directory size mismatch: {entry['dos_name']}")
        expected_date, expected_time, rendered = fat_datetime(expected["source_date_epoch"])
        observed_times = (
            entry["creation_date"], entry["access_date"], entry["write_date"],
            entry["creation_time"], entry["write_time"],
        )
        if observed_times != (expected_date, expected_date, expected_date, expected_time, expected_time):
            raise ValidationError(f"directory timestamp is not from SOURCE_DATE_EPOCH: {entry['dos_name']}")
        required_clusters = (entry["size"] + cluster_bytes - 1) // cluster_bytes
        cluster = entry["first_cluster"]
        chain = []
        local = set()
        while True:
            if not 2 <= cluster <= max_cluster:
                raise ValidationError(f"cluster is outside the data area: {entry['dos_name']}")
            if cluster in local:
                raise ValidationError(f"cluster-chain loop: {entry['dos_name']}")
            if cluster in all_used:
                raise ValidationError(f"cluster cross-link: {entry['dos_name']}")
            local.add(cluster)
            all_used.add(cluster)
            chain.append(cluster)
            value = get_fat12_entry(fat1, cluster)
            if 0xFF8 <= value <= 0xFFF:
                break
            if value == 0 or value == 0xFF7 or 0xFF0 <= value <= 0xFF6:
                raise ValidationError(f"invalid FAT12 chain marker: {entry['dos_name']}")
            cluster = value
        if len(chain) < required_clusters:
            raise ValidationError(f"directory size exceeds its cluster chain: {entry['dos_name']}")
        if len(chain) != required_clusters:
            raise ValidationError(f"cluster chain is longer than the directory size: {entry['dos_name']}")
        content = bytearray()
        for item in chain:
            lba = derived["first_data_sector"] + (item - 2) * filesystem["sectors_per_cluster"]
            content.extend(raw[lba * bps:lba * bps + cluster_bytes])
        payload = bytes(content[:entry["size"]])
        if sha256_bytes(payload) != expected["sha256"]:
            raise ValidationError(f"extracted payload SHA-256 mismatch: {entry['dos_name']}")
        if content[entry["size"]:] != bytes(len(content) - entry["size"]):
            raise ValidationError(f"allocated cluster tail is not zero: {entry['dos_name']}")
        extracted[entry["dos_name"]] = payload
        allocations.append({
            "clusters": chain,
            "dos_name": entry["dos_name"],
            "first_cluster": chain[0],
            "sha256": expected["sha256"],
            "size": entry["size"],
            "source_date_epoch": expected["source_date_epoch"],
            "fat_timestamp": {"fat_date": expected_date, "fat_time": expected_time, "utc": rendered},
        })
    for cluster in range(2, max_cluster + 1):
        value = get_fat12_entry(fat1, cluster)
        if cluster not in all_used and value != 0:
            raise ValidationError(f"unallocated FAT12 entry is not zero: cluster {cluster}")
        if cluster not in all_used:
            lba = derived["first_data_sector"] + (cluster - 2) * filesystem["sectors_per_cluster"]
            data = raw[lba * bps:lba * bps + cluster_bytes]
            if data != bytes(cluster_bytes):
                raise ValidationError(f"unallocated data cluster is not zero: cluster {cluster}")
    summary = {
        "allocations": allocations,
        "boot_record": boot_summary,
        "fat_1": {"sha256": sha256_bytes(fat1), "size": len(fat1)},
        "fat_2": {"sha256": sha256_bytes(fat2), "size": len(fat2)},
        "root_directory": {"sha256": sha256_bytes(root), "size": len(root)},
    }
    return summary, extracted


def parse_d88(d88_bytes: bytes, spec: dict, derived: dict) -> tuple[dict, bytes]:
    geometry = spec["geometry"]
    contract = spec["d88"]
    if len(d88_bytes) < contract["header_size"]:
        raise ValidationError("D88 header is truncated")
    declared = struct.unpack_from("<I", d88_bytes, 28)[0]
    if declared != len(d88_bytes) or declared != contract["declared_size"]:
        raise ValidationError("D88 declared size or trailing-data boundary is invalid")
    expected_name = contract["disk_name"].encode("ascii").ljust(17, b"\x00")
    if d88_bytes[:17] != expected_name or d88_bytes[17:26] != bytes(9):
        raise ValidationError("D88 disk name or reserved header bytes differ")
    if d88_bytes[26] != 0 or d88_bytes[27] != contract["disk_type"]:
        raise ValidationError("D88 write-protect or disk-type field differs")
    offsets = list(struct.unpack_from("<164I", d88_bytes, 32))
    populated = offsets[:contract["populated_tracks"]]
    if any(offsets[contract["populated_tracks"]:]):
        raise ValidationError("D88 contains unexpected hidden track offsets")
    if len(populated) != len(set(populated)) or populated != sorted(populated):
        raise ValidationError("D88 track offsets descend, overlap, or duplicate")
    if not populated or populated[0] != contract["header_size"] or any(item >= declared for item in populated):
        raise ValidationError("D88 track offset is outside the declared file")
    raw = bytearray()
    seen = set()
    sector_records = 0
    track_size = geometry["sectors_per_track"] * (
        contract["sector_header_size"] + geometry["bytes_per_sector"]
    )
    for track, start in enumerate(populated):
        expected_start = contract["header_size"] + track * track_size
        end = populated[track + 1] if track + 1 < len(populated) else declared
        if start != expected_start or end - start != track_size:
            raise ValidationError("D88 track offsets are overlapping, gapped, or out of bounds")
        cursor = start
        cylinder, head = divmod(track, geometry["heads"])
        for sector_index in range(geometry["sectors_per_track"]):
            if cursor + contract["sector_header_size"] > end:
                raise ValidationError("D88 sector header is truncated")
            fields = struct.unpack_from("<BBBBHBBBB3sBH", d88_bytes, cursor)
            c, h, r, n, count, mfm, deleted, status, seek, reserved, rpm, size = fields
            expected_chr = (cylinder, head, geometry["physical_sector_id_base"] + sector_index)
            if (c, h, r) in seen:
                raise ValidationError("D88 contains a duplicate CHR sector")
            seen.add((c, h, r))
            if (c, h, r) != expected_chr:
                raise ValidationError("D88 contains a missing, extra, or out-of-order CHR sector")
            if n != contract["sector_size_code"] or size != geometry["bytes_per_sector"]:
                raise ValidationError("D88 sector-size code or byte length differs")
            if count != geometry["sectors_per_track"]:
                raise ValidationError("D88 per-track sector count differs")
            if (mfm, deleted, status, seek, reserved, rpm) != (0, 0, 0, 0, b"\x00\x00\x00", 0):
                raise ValidationError("D88 density, deleted-data, error, or reserved status is nonzero")
            cursor += contract["sector_header_size"]
            if cursor + size > end:
                raise ValidationError("D88 sector payload is truncated or out of bounds")
            raw.extend(d88_bytes[cursor:cursor + size])
            cursor += size
            sector_records += 1
        if cursor != end:
            raise ValidationError("D88 track contains trailing or hidden sector data")
    if sector_records != derived["total_sectors"] or len(raw) != derived["total_bytes"]:
        raise ValidationError("D88 sector set does not reconstruct the M05 geometry")
    return {
        "declared_size": declared,
        "disk_type": d88_bytes[27],
        "populated_tracks": len(populated),
        "sector_count": sector_records,
        "sha256": sha256_bytes(d88_bytes),
        "size": len(d88_bytes),
    }, bytes(raw)


def validate_d88_round_trip(d88_bytes: bytes, raw: bytes, spec: dict, derived: dict) -> tuple[dict, bytes]:
    summary, reconstructed = parse_d88(d88_bytes, spec, derived)
    if reconstructed != raw:
        raise ValidationError("D88 extraction differs from the canonical raw image")
    return summary, reconstructed


def expected_record(record: dict) -> dict:
    return {
        "dos_name": record["dos_name"],
        "sha256": record["sha256"],
        "size": record["size"],
        "source_date_epoch": record["source_date_epoch"],
    }


def inspect_run(root: Path, run_dir: Path, write_outputs: bool) -> dict:
    spec, derived = validate_spec(root)
    validate_chs_round_trip(spec["geometry"])
    records = accepted_artifacts(root, spec)
    raw_path = run_dir / spec["image"]["raw_filename"]
    d88_path = run_dir / spec["image"]["d88_filename"]
    raw = raw_path.read_bytes()
    d88_bytes = d88_path.read_bytes()
    raw_summary, extracted = inspect_raw(raw, spec, derived, [expected_record(item) for item in records])
    d88_summary, reconstructed = validate_d88_round_trip(d88_bytes, raw, spec, derived)
    manifest = {
        "d88": d88_summary,
        "derived_layout": derived,
        "extracted_payloads": [
            {"dos_name": name, "sha256": sha256_bytes(extracted[name]), "size": len(extracted[name])}
            for name in sorted(extracted)
        ],
        "extracted_raw": {"sha256": sha256_bytes(reconstructed), "size": len(reconstructed)},
        "inspector_identities": {
            "common.py": sha256_file(Path(__file__).with_name("common.py")),
            "inspect_media.py": sha256_file(Path(__file__)),
        },
        "milestone": MILESTONE,
        "raw": {"sha256": sha256_bytes(raw), "size": len(raw)},
        "regions": raw_summary,
        "schema_version": 1,
        "unknowns": spec["unknowns"],
        "validation": {
            "d88_structure": "pass",
            "fat12_structure": "pass",
            "payload_extraction": "pass",
            "raw_d88_round_trip": "pass",
            "zero_unallocated_space": "pass",
        },
    }
    if write_outputs:
        extracted_dir = run_dir / "extracted"
        extracted_raw = run_dir / "extracted-raw.img"
        manifest_path = run_dir / "inspection-manifest.json"
        if extracted_dir.exists() or extracted_raw.exists() or manifest_path.exists():
            raise ValidationError("M05 inspection outputs already exist")
        extracted_dir.mkdir(mode=0o755)
        extracted_raw.write_bytes(reconstructed)
        os.chmod(extracted_raw, 0o644)
        for name, data in sorted(extracted.items()):
            path = extracted_dir / name
            path.write_bytes(data)
            os.chmod(path, 0o644)
        write_canonical_json(manifest_path, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    run_dir = args.run_dir if args.run_dir.is_absolute() else root / args.run_dir
    try:
        manifest = inspect_run(root, run_dir, True)
    except (OSError, OverflowError, ValueError, ValidationError) as exc:
        print(f"M05 inspection failed: {exc}", file=sys.stderr)
        return 1
    print(
        "M05 inspection passed: "
        f"raw={manifest['raw']['sha256']} d88={manifest['d88']['sha256']} round-trip=byte-identical"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
