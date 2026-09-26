#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Shared deterministic M05 contract, identity, and filesystem helpers."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


MILESTONE = "M05-deterministic-candidate-media"
START_COMMIT = "8b33ee3c6eece05ac4e810726d4dce90372ab4b3"
SPEC_RELATIVE = "config/m05/media.json"
SCHEMA_RELATIVE = "config/m05/media.schema.json"
GOLDEN_RELATIVE = "qa/golden/m05-media-manifest.json"
RESULTS_RELATIVE = "qa/results/m05"
M02_RUN_RELATIVE = "qa/results/m02/run-1/baseline-artifact-bundle"
EXPECTED_GITLINKS = {
    "country": "23f189cca3420606eae8723884fa92ccd65eb307",
    "fdkernel": "6523acdb87f4665e6068ea331859885267242005",
    "freecom": "855281a3114b43ad4b8d9a320f2aca39be046bba",
}
IDENTITY_PATHS = {
    "components_lock_sha256": "manifests/components.lock.json",
    "copying_sha256": "COPYING",
    "m01_contract_sha256": "manifests/m01-build-contract.json",
    "m01_golden_sha256": "qa/golden/m01-baseline.json",
    "m02_golden_sha256": "qa/golden/m02/bundle-manifest.json",
    "m03r1_golden_sha256": "qa/golden/m03/port-surface.json",
    "m04_contract_sha256": "config/contracts/m04-provisional-pc88va-boot-media.json",
    "m04_evidence_matrix_sha256": "config/contracts/m04-evidence-matrix.json",
    "m04_schema_sha256": "config/contracts/m04-provisional-pc88va-boot-media.schema.json",
    "toolchain_lock_sha256": "manifests/toolchains.lock.json",
}
EXPECTED_UNKNOWNS = [
    "firmware_boot_acceptance_rules",
    "required_boot_signature_or_checksum",
    "whether_firmware_loads_exactly_one_1024_byte_sector",
    "actual_entry_registers_flags_stack_and_interrupt_state",
    "boot_drive_identity_convention",
    "common_firmware_disk_service_entry_point",
    "pc88va_kernel_load_address_entry_point_and_handoff_state",
]
EXPECTED_BOOT_RECORD = {
    "extended_bpb_signature": 41,
    "filesystem_type": "FAT12",
    "oem_name": "FDPC88VA",
    "placeholder_code": [235, 254, 144],
    "placeholder_semantics": "x86_short_jump_minus_2_self_loop_then_unreached_nop",
    "signature_policy": "no_firmware_signature_at_offset_510_or_1022",
    "unassigned_byte_policy": "zero",
}
EXPECTED_D88 = {
    "declared_size": 1331888,
    "deleted_data": 0,
    "disk_name": "FD-PC88VA-M05",
    "disk_type": 32,
    "error_status": 0,
    "header_size": 688,
    "mfm_density_field": 0,
    "populated_tracks": 160,
    "rpm_field": 0,
    "sector_header_size": 16,
    "sector_size_code": 3,
    "track_table_entries": 164,
    "write_protect": 0,
}
EXPECTED_FILESYSTEM = {
    "data_clusters": 1269,
    "fat_bytes_required": 1907,
    "fat_count": 2,
    "fat_timestamp_policy": "per_payload_m02_source_date_epoch_utc_truncated_to_even_second",
    "fat_type": "FAT12",
    "first_data_sector": 11,
    "hidden_sectors": 0,
    "media_descriptor": 254,
    "reserved_sectors": 1,
    "root_directory_sectors": 6,
    "root_entries": 192,
    "sectors_per_cluster": 1,
    "sectors_per_fat": 2,
    "unallocated_data_policy": "zero",
}
EXPECTED_FORMAT_PROVENANCE = {
    "implementation_policy": "independent_minimal_writer_and_parser_no_code_copied",
    "paths": ["fdd/d88head.h", "fdd/fdd_d88.c", "fdd/newdisk.c"],
    "repository": "https://github.com/nakatamaho/vaeg.git",
    "revision": "2a6c3944bab1fb691261fa2f0950dc4a2faeab8c",
}
EXPECTED_GEOMETRY = {
    "bytes_per_sector": 1024,
    "cylinders": 80,
    "encoding": "MFM",
    "heads": 2,
    "physical_sector_id_base": 1,
    "sectors_per_track": 8,
    "total_bytes": 1310720,
    "total_sectors": 1280,
    "track_order": "cylinder_major_head_minor",
}
EXPECTED_IMAGE = {
    "d88_filename": "pc88va-m05-candidate.d88",
    "raw_filename": "pc88va-m05-candidate.img",
    "volume_label": "PC88VA-M05",
    "volume_serial": 1446326349,
}
EXPECTED_PAYLOADS = [
    {
        "bundle_path": "payload/fdkernel/KERNEL.SYS",
        "dos_name": "KERNEL.SYS",
        "runtime_claim": "nec98_reference_for_packaging_validation_only",
        "source_role": "kernel",
    },
    {
        "bundle_path": "payload/freecom/COMMAND.COM",
        "dos_name": "COMMAND.COM",
        "runtime_claim": "nec98_japanese_reference_for_packaging_validation_only",
        "source_role": "command-interpreter",
    },
    {
        "bundle_path": "payload/fdos-country/COUNTRY.SYS",
        "dos_name": "COUNTRY.SYS",
        "runtime_claim": "standalone_country_reference_for_packaging_validation_only",
        "source_role": "standalone-country-driver",
    },
]
PRIVATE_MARKERS = (
    "private-source-root",
    "private-evidence",
    "m04-private",
    "private-overlay",
    ".rom",
)
UNSTABLE_KEYS = {
    "absolute_path", "created_at", "cwd", "generated_at", "hostname",
    "host_architecture", "temporary_path", "timestamp", "username",
}
DOS_NAME_RE = re.compile(r"^[A-Z0-9!#$%&'()@^_`{}~-]{1,8}(?:\.[A-Z0-9!#$%&'()@^_`{}~-]{1,3})?$")


class ValidationError(RuntimeError):
    """Raised for a bounded fail-closed M05 contract error."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value) -> bytes:
    reject_ambient_metadata(value)
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def load_canonical_json(path: Path):
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot parse JSON {path}: {exc}") from exc
    if path.read_bytes() != canonical_json_bytes(data):
        raise ValidationError(f"JSON is not canonical: {path}")
    return data


def write_canonical_json(path: Path, value) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))
    os.chmod(path, 0o644)


def reject_ambient_metadata(value, label="metadata") -> None:
    if isinstance(value, float):
        raise ValidationError(f"floating-point value is not canonical: {label}")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValidationError(f"non-string JSON key: {label}")
            if key.lower() in UNSTABLE_KEYS:
                raise ValidationError(f"ambient metadata field is prohibited: {label}.{key}")
            reject_ambient_metadata(item, f"{label}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            reject_ambient_metadata(item, f"{label}[{index}]")
    elif isinstance(value, str):
        lower = value.lower()
        if value.startswith(("/", "file://")) or re.match(r"^[A-Za-z]:[\\/]", value):
            raise ValidationError(f"absolute path is prohibited: {label}")
        if any(marker in lower for marker in PRIVATE_MARKERS):
            raise ValidationError(f"private input marker is prohibited: {label}")


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ("git", *args), cwd=root, check=False, capture_output=True, text=True
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise ValidationError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def regular_file(path: Path, label: str) -> os.stat_result:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ValidationError(f"cannot stat {label}: {path}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValidationError(f"{label} is not a non-hard-linked regular file: {path}")
    return info


def validate_repository(root: Path, spec: dict) -> None:
    root = root.resolve()
    if root.name != "freedos-pc88va" or Path(run_git(root, "rev-parse", "--show-toplevel").strip()).resolve() != root:
        raise ValidationError("repository root identity mismatch")
    if subprocess.run(
        ("git", "merge-base", "--is-ancestor", START_COMMIT, "HEAD"),
        cwd=root,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode:
        raise ValidationError("accepted M04R1 commit is not an ancestor of HEAD")
    if spec["parent_commit"] != START_COMMIT:
        raise ValidationError("M05 specification parent identity mismatch")
    for name, expected in EXPECTED_GITLINKS.items():
        relative = f"components/{name}"
        fields = run_git(root, "ls-files", "--stage", "--", relative).strip().split()
        if len(fields) < 4 or fields[0] != "160000" or fields[1] != expected:
            raise ValidationError(f"component gitlink mismatch: {relative}")
        if run_git(root, "-C", relative, "rev-parse", "HEAD").strip() != expected:
            raise ValidationError(f"component checkout mismatch: {relative}")
        if run_git(root, "-C", relative, "status", "--short", "--untracked-files=all"):
            raise ValidationError(f"component worktree is dirty: {relative}")
    validate_component_contract(spec["component_gitlinks"])
    for key, relative in IDENTITY_PATHS.items():
        actual = sha256_file(root / relative)
        if spec["consumed_identities"].get(key) != actual:
            raise ValidationError(f"consumed identity mismatch: {relative}: {actual}")


def validate_component_contract(component_gitlinks: dict) -> None:
    if component_gitlinks != EXPECTED_GITLINKS:
        raise ValidationError("component identities in the M05 specification differ")


def derive_layout(spec: dict) -> dict:
    geometry = spec["geometry"]
    filesystem = spec["filesystem"]
    bps = require_positive_int(geometry, "bytes_per_sector")
    cylinders = require_positive_int(geometry, "cylinders")
    heads = require_positive_int(geometry, "heads")
    spt = require_positive_int(geometry, "sectors_per_track")
    total_sectors = cylinders * heads * spt
    total_bytes = total_sectors * bps
    root_entries = require_positive_int(filesystem, "root_entries")
    root_sectors = (root_entries * 32 + bps - 1) // bps
    reserved = require_positive_int(filesystem, "reserved_sectors")
    fat_count = require_positive_int(filesystem, "fat_count")
    sectors_per_fat = require_positive_int(filesystem, "sectors_per_fat")
    sectors_per_cluster = require_positive_int(filesystem, "sectors_per_cluster")
    first_data = reserved + fat_count * sectors_per_fat + root_sectors
    data_sectors = total_sectors - first_data
    if data_sectors <= 0 or data_sectors % sectors_per_cluster:
        raise ValidationError("data region does not contain an integral cluster count")
    data_clusters = data_sectors // sectors_per_cluster
    fat_entries = data_clusters + 2
    fat_bytes_required = (fat_entries * 3 + 1) // 2
    fat_capacity = sectors_per_fat * bps
    if data_clusters >= 4085:
        raise ValidationError("derived cluster count is not FAT12")
    if fat_capacity < fat_bytes_required:
        raise ValidationError("FAT region cannot represent every data cluster")
    derived = {
        "data_clusters": data_clusters,
        "data_sectors": data_sectors,
        "fat_bytes_required": fat_bytes_required,
        "fat_capacity_bytes": fat_capacity,
        "first_data_sector": first_data,
        "root_directory_sectors": root_sectors,
        "total_bytes": total_bytes,
        "total_sectors": total_sectors,
    }
    declared = {
        "data_clusters": filesystem["data_clusters"],
        "fat_bytes_required": filesystem["fat_bytes_required"],
        "first_data_sector": filesystem["first_data_sector"],
        "root_directory_sectors": filesystem["root_directory_sectors"],
        "total_bytes": geometry["total_bytes"],
        "total_sectors": geometry["total_sectors"],
    }
    for key, value in declared.items():
        if derived[key] != value:
            raise ValidationError(f"declared M05 layout does not recompute: {key}")
    expected_d88 = spec["d88"]["header_size"] + total_sectors * (
        spec["d88"]["sector_header_size"] + bps
    )
    if spec["d88"]["declared_size"] != expected_d88:
        raise ValidationError("declared D88 size does not recompute")
    derived["d88_size"] = expected_d88
    return derived


def require_positive_int(mapping: dict, key: str) -> int:
    value = mapping.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValidationError(f"{key} must be a positive integer")
    return value


def validate_spec(root: Path) -> tuple[dict, dict]:
    spec = load_canonical_json(root / SPEC_RELATIVE)
    schema = load_canonical_json(root / SCHEMA_RELATIVE)
    required = {
        "boot_record", "component_gitlinks", "consumed_identities", "d88",
        "filesystem", "format_provenance", "geometry", "image", "milestone",
        "parent_commit", "payloads", "schema_version", "unknowns",
    }
    if set(spec) != required or spec["schema_version"] != 1 or spec["milestone"] != MILESTONE:
        raise ValidationError("M05 media specification schema is invalid")
    validate_schema_contract(schema, required)
    if spec["unknowns"] != EXPECTED_UNKNOWNS:
        raise ValidationError("M04 unknowns were removed, reordered, or invented in M05")
    fixed_sections = {
        "boot_record": EXPECTED_BOOT_RECORD,
        "d88": EXPECTED_D88,
        "filesystem": EXPECTED_FILESYSTEM,
        "format_provenance": EXPECTED_FORMAT_PROVENANCE,
        "geometry": EXPECTED_GEOMETRY,
        "image": EXPECTED_IMAGE,
        "payloads": EXPECTED_PAYLOADS,
    }
    for key, expected in fixed_sections.items():
        if spec.get(key) != expected:
            raise ValidationError(f"fixed M05 contract section changed: {key}")
    names = [item["dos_name"] for item in spec["payloads"]]
    if len(names) != len(set(names)):
        raise ValidationError("duplicate DOS filename in M05 specification")
    for item in spec["payloads"]:
        encode_dos_name(item["dos_name"])
        safe_relative_path(item["bundle_path"], "M02 bundle path")
    reject_ambient_metadata(spec, "M05 specification")
    derived = derive_layout(spec)
    validate_repository(root, spec)
    return spec, derived


def validate_schema_contract(schema: dict, required_fields: set[str]) -> None:
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise ValidationError("M05 schema dialect changed")
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        raise ValidationError("M05 schema top-level object is not fail-closed")
    if set(schema.get("properties", {})) != required_fields:
        raise ValidationError("M05 schema properties differ from the specification contract")
    if schema.get("required") != sorted(required_fields):
        raise ValidationError("M05 schema required-field order or membership differs")
    if schema["properties"].get("schema_version", {}).get("const") != 1:
        raise ValidationError("M05 schema version constraint differs")
    if schema["properties"].get("milestone", {}).get("const") != MILESTONE:
        raise ValidationError("M05 schema milestone constraint differs")


def safe_relative_path(value: str, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or not value.isascii() or "\\" in value:
        raise ValidationError(f"unsafe {label}: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        raise ValidationError(f"unsafe {label}: {value!r}")
    return path


def encode_dos_name(value: str) -> bytes:
    if not isinstance(value, str) or not value.isascii() or value != value.upper() or not DOS_NAME_RE.fullmatch(value):
        raise ValidationError(f"DOS filename is not lossless uppercase 8.3 ASCII: {value!r}")
    parts = value.split(".", 1)
    base = parts[0].encode("ascii").ljust(8, b" ")
    extension = (parts[1] if len(parts) == 2 else "").encode("ascii").ljust(3, b" ")
    return base + extension


def decode_dos_name(value: bytes) -> str:
    if len(value) != 11:
        raise ValidationError("DOS directory name is not 11 bytes")
    try:
        base = value[:8].decode("ascii").rstrip(" ")
        extension = value[8:].decode("ascii").rstrip(" ")
    except UnicodeDecodeError as exc:
        raise ValidationError("DOS directory name is not ASCII") from exc
    name = base + (("." + extension) if extension else "")
    if encode_dos_name(name) != value:
        raise ValidationError("DOS directory name is noncanonical")
    return name


def chs_to_lba(cylinder: int, head: int, sector_id: int, geometry: dict) -> int:
    cylinders = geometry["cylinders"]
    heads = geometry["heads"]
    spt = geometry["sectors_per_track"]
    base = geometry["physical_sector_id_base"]
    if not 0 <= cylinder < cylinders or not 0 <= head < heads or not base <= sector_id < base + spt:
        raise ValidationError("CHS address is outside the M05 geometry")
    return ((cylinder * heads) + head) * spt + (sector_id - base)


def lba_to_chs(lba: int, geometry: dict) -> tuple[int, int, int]:
    total = geometry["total_sectors"]
    if not isinstance(lba, int) or isinstance(lba, bool) or not 0 <= lba < total:
        raise ValidationError("LBA is outside the M05 geometry")
    heads = geometry["heads"]
    spt = geometry["sectors_per_track"]
    base = geometry["physical_sector_id_base"]
    cylinder, remainder = divmod(lba, heads * spt)
    head, sector = divmod(remainder, spt)
    return cylinder, head, sector + base


def validate_chs_round_trip(geometry: dict) -> None:
    for lba in range(geometry["total_sectors"]):
        if chs_to_lba(*lba_to_chs(lba, geometry), geometry) != lba:
            raise ValidationError(f"CHS/LBA round trip failed at LBA {lba}")


def fat_datetime(source_date_epoch: int) -> tuple[int, int, str]:
    if not isinstance(source_date_epoch, int) or isinstance(source_date_epoch, bool):
        raise ValidationError("source_date_epoch must be an integer")
    value = datetime.fromtimestamp(source_date_epoch, timezone.utc)
    if not 1980 <= value.year <= 2107:
        raise ValidationError("source_date_epoch is outside the FAT timestamp range")
    fat_date = ((value.year - 1980) << 9) | (value.month << 5) | value.day
    fat_time = (value.hour << 11) | (value.minute << 5) | (value.second // 2)
    rendered = value.replace(second=value.second & ~1, microsecond=0).isoformat().replace("+00:00", "Z")
    return fat_date, fat_time, rendered


def accepted_artifacts(root: Path, spec: dict) -> list[dict]:
    golden = load_canonical_json(root / "qa/golden/m02/bundle-manifest.json")
    records = golden.get("artifacts")
    if not isinstance(records, list):
        raise ValidationError("M02 golden artifact list is missing")
    by_role = {item.get("role"): item for item in records}
    if len(by_role) != len(records):
        raise ValidationError("M02 golden contains a duplicate role")
    selected = []
    for requested in spec["payloads"]:
        record = by_role.get(requested["source_role"])
        if record is None or record.get("bundle_path") != requested["bundle_path"]:
            raise ValidationError(f"M02 role/path mismatch: {requested['source_role']}")
        merged = dict(record)
        merged.update({
            "dos_name": requested["dos_name"],
            "runtime_claim": requested["runtime_claim"],
            "source_role": requested["source_role"],
        })
        source = root / M02_RUN_RELATIVE / safe_relative_path(record["bundle_path"], "M02 payload path")
        info = regular_file(source, "verified M02 payload")
        if info.st_size != record["size"] or sha256_file(source) != record["sha256"]:
            raise ValidationError(f"M02 payload identity mismatch: {record['bundle_path']}")
        merged["source_path"] = source
        selected.append(merged)
    validate_payload_contract(selected)
    return selected


def validate_payload_contract(records: list[dict]) -> None:
    by_name = {item.get("dos_name"): item for item in records}
    if len(by_name) != len(records) or set(by_name) != {"KERNEL.SYS", "COMMAND.COM", "COUNTRY.SYS"}:
        raise ValidationError("M05 payload filename set is incomplete or duplicated")
    kernel = by_name["KERNEL.SYS"]
    if kernel.get("source_role") != "kernel" or kernel.get("size") != 83774 or kernel.get("sha256") != "3ebddb01abe5e39f16d27439836be283c57d454f012d3c990f01fa8a2b14101d":
        raise ValidationError("M05 kernel is not the accepted M01R1 reference identity")
    command = by_name["COMMAND.COM"]
    if command.get("source_role") != "command-interpreter" or command.get("size") != 91143 or command.get("sha256") != "fabe7744cc7c51c6f72519cc39d89bf77beaf908f994675a97a1e34c93549da1":
        raise ValidationError("M05 COMMAND.COM is not the accepted M02 identity")
    country = by_name["COUNTRY.SYS"]
    if country.get("source_role") != "standalone-country-driver" or country.get("size") != 42614 or country.get("sha256") != "04b2d2bc8df382090686f00e547d718d6706d22fb34c34dd77cd55083d5c34d5":
        raise ValidationError("M05 COUNTRY.SYS is not the standalone Country artifact")


def run_m02_verifier(root: Path) -> None:
    result = subprocess.run(
        (os.environ.get("PYTHON", "python3"), "tools/m02/verify_bundle.py"),
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if result.returncode:
        detail = (result.stdout + result.stderr).strip().replace("\n", " | ")
        raise ValidationError(f"accepted M02 verifier rejected candidate inputs: {detail}")
    print(result.stdout.strip())


def remove_owned_results(root: Path) -> None:
    target = root.resolve() / RESULTS_RELATIVE
    expected = root.resolve() / "qa" / "results" / "m05"
    if target != expected:
        raise ValidationError("refusing to clean an unresolved M05 result path")
    if target.is_symlink():
        raise ValidationError("refusing to clean a symlinked M05 result path")
    if target.exists():
        shutil.rmtree(target)


def file_identity(path: Path) -> dict:
    info = regular_file(Path(path), "generated M05 file")
    return {"sha256": sha256_file(path), "size": info.st_size}
