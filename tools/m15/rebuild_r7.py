#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Reproduce the r6 M15 disk as r7 and prove sector-level equivalence.

The private input profile binds the recovered r6 D88, source locks, and the
major rebuilt binaries.  The r6 image is an immutable seed; this tool parses
and rebuilds its D88 container twice, verifies every FAT12 payload, and emits
one r7 image only after both independent passes agree.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import struct
import subprocess
import sys
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / ".private-evidence"
sys.path[:0] = [str(ROOT / "tools/m15")]

from media import build_d88  # noqa: E402
from media import derive_layout  # noqa: E402
from media import inspect as inspect_fat12  # noqa: E402
from media import parse_d88  # noqa: E402


FORMAT = "m15-r7-input-profile-v1"
SOURCE_KEYS = {
    "parent_baseline_commit",
    "fdkernel_commit",
    "freecom_commit",
    "country_commit",
    "m13_carrier_fix_commit",
    "carrier_builder_blob_sha1",
    "fixture_source_commit",
    "sysva_source_commit",
}
REQUIRED_REBUILDS = {
    "KERNEL.SYS",
    "LOADER.BIN",
    "COMMAND.COM",
    "COUNTRY.SYS",
    "SYSVA.EXE",
    "SYSQA.COM",
    "ALIASQA.COM",
    "NLSTABLE.COM",
    "NLSQA.COM",
    "SYSMISC.COM",
    "CONSOLE.COM",
    "FCBQA.COM",
}
DOS_NAME = re.compile(r"^[A-Z0-9!#$%&'()@^_`{}~-]{1,8}(?:\.[A-Z0-9!#$%&'()@^_`{}~-]{1,3})?$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class RebuildError(ValueError):
    """Raised when r6 inputs are incomplete or do not reproduce r7."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identity(data: bytes) -> dict[str, int | str]:
    return {"size": len(data), "sha256": sha256(data)}


def file_identity(path: Path) -> dict[str, int | str]:
    return identity(path.read_bytes())


def is_under(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def reject_symlink_path(path: Path) -> None:
    if any(item.is_symlink() for item in (path, *path.parents)):
        raise RebuildError("input or output path traverses a symlink")


def validate_profile(profile: object) -> dict:
    if not isinstance(profile, dict) or set(profile) != {
        "format", "candidate_id", "source_lock", "seed_media", "payloads"
    }:
        raise RebuildError("profile fields differ from the r7 recipe contract")
    if profile["format"] != FORMAT or profile["candidate_id"] != "M15-QA-r6":
        raise RebuildError("profile is not bound to the recovered r6 candidate")

    sources = profile["source_lock"]
    if not isinstance(sources, dict) or set(sources) != SOURCE_KEYS:
        raise RebuildError("source lock fields differ from the r7 recipe contract")
    if any(not isinstance(sources[key], str) or HEX40.fullmatch(sources[key]) is None
           for key in SOURCE_KEYS):
        raise RebuildError("source lock contains a malformed 40-hex identity")
    seed = profile["seed_media"]
    if (not isinstance(seed, dict) or set(seed) != {"size", "sha256"}
            or type(seed["size"]) is not int or seed["size"] <= 0
            or not isinstance(seed["sha256"], str)
            or HEX64.fullmatch(seed["sha256"]) is None):
        raise RebuildError("seed identity is malformed")

    payloads = profile["payloads"]
    if not isinstance(payloads, list) or not payloads:
        raise RebuildError("payload source list is empty or malformed")
    names = set()
    rebuilt = set()
    for item in payloads:
        if not isinstance(item, dict) or "dos_name" not in item or "origin" not in item:
            raise RebuildError("payload source record is malformed")
        name = item["dos_name"]
        if not isinstance(name, str) or DOS_NAME.fullmatch(name) is None:
            raise RebuildError("payload DOS name is not canonical uppercase 8.3")
        if name in names:
            raise RebuildError("duplicate payload source record")
        names.add(name)
        if item["origin"] == "source_build":
            if set(item) != {"dos_name", "origin", "path", "size", "sha256", "source"}:
                raise RebuildError("source-built payload record is incomplete or has unknown fields")
            rel = PurePosixPath(item["path"]) if isinstance(item["path"], str) else None
            if rel is None or rel.is_absolute() or "" in rel.parts:
                raise RebuildError("source-built payload path must be relative")
            if type(item["size"]) is not int or item["size"] <= 0:
                raise RebuildError("source-built payload size is invalid")
            if not isinstance(item["sha256"], str) or HEX64.fullmatch(item["sha256"]) is None:
                raise RebuildError("source-built payload SHA-256 is malformed")
            if not isinstance(item["source"], str) or not item["source"].strip():
                raise RebuildError("source-built payload has no source binding")
            rebuilt.add(name)
        elif item["origin"] == "r6_seed":
            if set(item) != {"dos_name", "origin", "reason"}:
                raise RebuildError("seed-preserved payload record is incomplete or has unknown fields")
            if not isinstance(item["reason"], str) or not item["reason"].strip():
                raise RebuildError("seed-preserved payload must explain its retained source")
        else:
            raise RebuildError("payload origin must be source_build or r6_seed")
    missing = REQUIRED_REBUILDS - rebuilt
    if missing:
        raise RebuildError("mandatory rebuilt payloads are missing: " + ", ".join(sorted(missing)))
    return profile


def git_output(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def validate_source_lock(profile: dict) -> dict[str, str]:
    lock = profile["source_lock"]
    current = git_output("rev-parse", "HEAD")
    for commit in (lock["parent_baseline_commit"], lock["m13_carrier_fix_commit"],
                   lock["fixture_source_commit"]):
        subprocess.run(["git", "merge-base", "--is-ancestor", commit, current],
                       cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
    expected_gitlinks = {
        "components/fdkernel": lock["fdkernel_commit"],
        "components/freecom": lock["freecom_commit"],
        "components/country": lock["country_commit"],
    }
    observed = {}
    for path, expected in expected_gitlinks.items():
        line = git_output("ls-tree", "HEAD", path)
        fields = line.split()
        if len(fields) < 4 or fields[0] != "160000" or fields[1] != "commit" or fields[3] != path:
            raise RebuildError("source lock does not resolve to the expected component gitlink")
        if fields[2] != expected:
            raise RebuildError("component gitlink differs from the r6 source lock")
        observed[path] = fields[2]
    component_head = git_output("-C", str(ROOT / "components/fdkernel"), "rev-parse", "HEAD")
    if component_head != lock["fdkernel_commit"]:
        raise RebuildError("checked-out fdkernel differs from the parent gitlink")
    subprocess.run(["git", "-C", str(ROOT / "components/fdkernel"), "merge-base",
                    "--is-ancestor", lock["sysva_source_commit"], component_head],
                   cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)
    subprocess.run(["git", "diff", "--quiet", lock["fixture_source_commit"], current,
                    "--", "tests/m15/fixtures"], cwd=ROOT, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    builder = git_output("rev-parse", "HEAD:tools/m15/build_compressed_kernel.py")
    if builder != lock["carrier_builder_blob_sha1"]:
        raise RebuildError("M13 carrier builder differs from the r6 source lock")
    observed["parent_head"] = current
    observed["sysva_source_commit"] = lock["sysva_source_commit"]
    observed["carrier_builder_blob_sha1"] = builder
    return observed


def safe_payload_file(profile_path: Path, item: dict) -> Path:
    path = profile_path.parent / PurePosixPath(item["path"])
    resolved = path.resolve(strict=True)
    reject_symlink_path(path)
    evidence = EVIDENCE.resolve(strict=True)
    if not is_under(resolved, evidence) or not resolved.is_file():
        raise RebuildError("rebuilt payload input must be a regular file under private evidence")
    return resolved


def load_payloads(profile_path: Path, profile: dict) -> dict[str, dict]:
    result = {}
    for item in profile["payloads"]:
        if item["origin"] == "source_build":
            artifact = safe_payload_file(profile_path, item)
            data = artifact.read_bytes()
            if len(data) != item["size"] or sha256(data) != item["sha256"]:
                raise RebuildError("rebuilt payload differs from its private recipe binding")
            result[item["dos_name"]] = {
                "origin": item["origin"],
                "source": item["source"],
                "size": len(data),
                "sha256": sha256(data),
                "data": data,
            }
        else:
            result[item["dos_name"]] = {
                "origin": item["origin"],
                "source": item["reason"],
            }
    return result


def build_once(seed: bytes, profile: dict, payload_sources: dict[str, dict]) -> tuple[bytes, dict]:
    if len(seed) != profile["seed_media"]["size"] or sha256(seed) != profile["seed_media"]["sha256"]:
        raise RebuildError("r6 seed D88 does not match the private recipe binding")
    spec = json.loads((ROOT / "config/m15/media.json").read_text(encoding="utf-8"))
    if len(seed) < 17:
        raise RebuildError("r6 seed D88 header is truncated")
    try:
        disk_name = seed[:17].split(b"\x00", 1)[0].decode("ascii")
    except UnicodeDecodeError as exc:
        raise RebuildError("r6 seed D88 name is not ASCII") from exc
    spec["d88"]["disk_name"] = disk_name
    layout = derive_layout(spec)
    seed_summary, seed_raw = parse_d88(seed, spec, layout)
    seed_report, seed_files = inspect_fat12(seed, spec)
    if set(seed_files) != set(payload_sources):
        raise RebuildError("payload source list does not cover the exact r6 live-file set")
    payload_report = []
    for name in sorted(seed_files):
        data = seed_files[name]
        source = payload_sources[name]
        if source["origin"] == "source_build":
            if source["data"] != data:
                raise RebuildError("source-built payload differs from the r6 file: " + name)
            record = {key: value for key, value in source.items() if key != "data"}
            record["matches_r6_payload"] = True
        else:
            record = {
                "origin": source["origin"],
                "source": source["source"],
                "size": len(data),
                "sha256": sha256(data),
                "matches_r6_payload": True,
            }
        payload_report.append({"dos_name": name, **record})

    # Repacking is expected to retain every logical sector exactly.  D88 file
    # hashes may change if a future canonical header encoding changes.
    output = build_d88(spec, seed_raw)
    output_summary, output_raw = parse_d88(output, spec, layout)
    output_report, output_files = inspect_fat12(output, spec)
    if output_raw != seed_raw or output_files != seed_files:
        raise RebuildError("r7 repack changed logical sectors or FAT12 payload contents")
    if ((seed_summary["sector_count"], seed_summary["populated_tracks"], seed_summary["disk_type"])
            != (output_summary["sector_count"], output_summary["populated_tracks"], output_summary["disk_type"])):
        raise RebuildError("r7 repack changed D88 geometry or disk type")
    if set(seed_report["files"]) != set(output_report["files"]):
        raise RebuildError("r7 repack changed the live FAT12 directory")
    return output, {
        "input_d88": identity(seed),
        "output_d88": identity(output),
        "exact_d88_match": output == seed,
        "logical_sector_bytes_identical": output_raw == seed_raw,
        "live_files": payload_report,
        "live_file_count": len(seed_files),
        "allocated_cluster_count_unchanged":
            seed_report["allocated_clusters"] == output_report["allocated_clusters"],
        "fat_copy_count_unchanged":
            seed_report["fat_copies_equal"] and output_report["fat_copies_equal"],
    }


def require_private_output(output: Path) -> Path:
    evidence = EVIDENCE.resolve(strict=True)
    parent = output.parent.resolve(strict=True)
    if not is_under(parent, evidence) or parent == evidence:
        raise RebuildError("r7 output directory must be a child of .private-evidence")
    reject_symlink_path(output)
    if output.exists():
        raise RebuildError("r7 output directory already exists")
    probe = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", str(output)],
                           check=False)
    if probe.returncode:
        raise RebuildError("r7 output directory is not Git-ignored")
    output.mkdir(mode=0o700)
    if stat.S_IMODE(output.stat().st_mode) & 0o077:
        raise RebuildError("r7 output directory is not owner-only")
    return output


def run(args: argparse.Namespace) -> dict:
    profile_path = args.profile.resolve(strict=True)
    seed_path = args.seed.resolve(strict=True)
    reject_symlink_path(args.profile)
    reject_symlink_path(args.seed)
    if not is_under(profile_path, EVIDENCE.resolve(strict=True)) or not profile_path.is_file():
        raise RebuildError("r7 input profile must remain under private evidence")
    if not is_under(seed_path, EVIDENCE.resolve(strict=True)) or not seed_path.is_file():
        raise RebuildError("r6 seed D88 must remain under private evidence")
    try:
        profile = validate_profile(json.loads(profile_path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RebuildError("r7 input profile cannot be read") from exc
    source_observation = validate_source_lock(profile)
    payload_sources = load_payloads(profile_path, profile)
    output_dir = require_private_output(args.output.resolve())

    first, first_record = build_once(seed_path.read_bytes(), profile, payload_sources)
    second, second_record = build_once(seed_path.read_bytes(), profile, payload_sources)
    if first != second or first_record != second_record:
        raise RebuildError("two independent r7 rebuild passes differ")
    media_path = output_dir / "media.d88"
    with media_path.open("xb") as stream:
        stream.write(first)
    record = {
        "format": "m15-r7-reproduction-record-v1",
        "candidate_id": "M15-QA-r7",
        "source_candidate_id": profile["candidate_id"],
        "source_lock": profile["source_lock"],
        "source_observation": source_observation,
        "seed_media": profile["seed_media"],
        "recipe_sha256": sha256(Path(__file__).read_bytes()),
        "two_independent_rebuilds_equal": True,
        "substantial_equivalence": {
            "same_live_file_set": True,
            "same_live_file_contents": True,
            "same_logical_sector_bytes": True,
            "same_fat12_structure": True,
            "exact_d88_bytes": first == seed_path.read_bytes(),
        },
        "rebuild": first_record,
        "r7_media": file_identity(media_path),
    }
    record_path = output_dir / "reproduction.json"
    with record_path.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, sort_keys=True, indent=2)
        stream.write("\n")
    record_path.chmod(0o600)
    print("M15 r7 rebuilt twice; all live files and logical sectors match the r6 seed")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        run(args)
    except (OSError, RebuildError, subprocess.CalledProcessError, ValueError,
            KeyError, TypeError, struct.error) as exc:
        print("M15 r7 reproduction failed: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
