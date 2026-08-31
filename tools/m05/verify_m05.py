#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Preflight, verify, clean, and explicitly enroll M05 evidence."""

from __future__ import annotations

import argparse
import os
import stat
import sys
from pathlib import Path

import common as m05_common
from build_media import serializable_record
from common import (
    GOLDEN_RELATIVE,
    MILESTONE,
    RESULTS_RELATIVE,
    SCHEMA_RELATIVE,
    SPEC_RELATIVE,
    ValidationError,
    accepted_artifacts,
    file_identity,
    load_canonical_json,
    remove_owned_results,
    run_git,
    run_m02_verifier,
    sha256_file,
    validate_chs_round_trip,
    validate_spec,
    write_canonical_json,
)
from compare_media import compare_runs, tree_snapshot
from inspect_media import inspect_run

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "qa"))
from current_components import CurrentComponentError, resolve_current_components


def validate_descendant_spec(root: Path) -> tuple[dict, dict]:
    """Validate immutable M05 data while accepting an exact M06 gitlink overlay."""
    historical = dict(m05_common.EXPECTED_GITLINKS)
    historical_by_path = {f"components/{name}": commit for name, commit in historical.items()}
    try:
        current_by_path = resolve_current_components(root, historical_by_path)
    except CurrentComponentError as exc:
        raise ValidationError(str(exc)) from exc
    if current_by_path == historical_by_path:
        return validate_spec(root)
    current_by_name = {Path(path).name: commit for path, commit in current_by_path.items()}
    def validate_historical_contract(component_gitlinks: dict) -> None:
        if component_gitlinks != historical:
            raise ValidationError("component identities in the M05 specification differ")

    m05_common.EXPECTED_GITLINKS = current_by_name
    m05_common.validate_component_contract = validate_historical_contract
    return validate_spec(root)


def verify_tracked_safety(root: Path) -> None:
    forbidden_suffixes = {
        ".rom", ".d88", ".d98", ".hdi", ".hdd", ".img", ".ima", ".iso",
        ".bin", ".obj", ".o", ".exe", ".com", ".sys", ".tar", ".zip", ".log",
    }
    forbidden = []
    for relative in [item for item in run_git(root, "ls-files", "-z").split("\0") if item]:
        lower = relative.lower()
        if Path(lower).suffix in forbidden_suffixes:
            forbidden.append(relative)
        if lower.startswith(("qa/results/", "private/", "local/")):
            forbidden.append(relative)
        if "private-source-root" in lower or "private-evidence" in lower:
            forbidden.append(relative)
    if forbidden:
        raise ValidationError("forbidden tracked M05 input or output: " + ", ".join(sorted(set(forbidden))))


def validate_changed_paths(root: Path) -> None:
    changed = set(run_git(root, "diff", "--name-only", "8b33ee3c6eece05ac4e810726d4dce90372ab4b3").splitlines())
    changed.update(run_git(root, "diff", "--cached", "--name-only").splitlines())
    exact = {
        ".github/workflows/m05-media.yml",
        ".gitignore",
        "Makefile",
        "docs/porting/m05-media-image.md",
        "qa/golden/m05-media-manifest.json",
        "tests/m04/test_verify_m04.py",
        "tools/m04/verify_m04.py",
        ".github/workflows/m06-kernel.yml",
        ".github/workflows/m01-baseline.yml",
        ".github/workflows/scaffold.yml",
        "components/fdkernel",
        "manifests/README.md",
        "manifests/m06-components.lock.json",
        "qa/golden/m06-kernel-manifest.json",
        "schema/m06-kernel-interface.schema.json",
        "tools/m01/build_baseline.sh",
        "tools/m01/verify_m01.py",
        "tools/m02/common.py",
        "tools/m03/scan_port_surface.py",
        "tools/m03/verify_m03.py",
        "tools/m05/common.py",
        "tools/m05/verify_m05.py",
        "tools/qa/current_components.py",
        "tools/qa/verify_license_policy.py",
        "tools/verify_scaffold.py",
    }
    prefixes = (
        "config/m05/", "tests/m05/", "tools/m05/", "config/m06/",
        "docs/porting/m06-", "tests/m06/", "tools/m06/",
    )
    for relative in sorted(item for item in changed if item):
        if relative not in exact and not relative.startswith(prefixes):
            raise ValidationError(f"path is outside M05 parent-only scope: {relative}")


def preflight(root: Path, run_m02: bool = True) -> tuple[dict, dict, list[dict]]:
    spec, derived = validate_descendant_spec(root)
    validate_chs_round_trip(spec["geometry"])
    if run_m02:
        run_m02_verifier(root)
    records = accepted_artifacts(root, spec)
    verify_tracked_safety(root)
    validate_changed_paths(root)
    print("M05 preflight passed: M04 geometry, M02 inputs, license-era parent, components, and public boundary are valid")
    return spec, derived, records


def verify_build_manifest(root: Path, run_dir: Path, spec: dict, derived: dict, records: list[dict]) -> dict:
    manifest = load_canonical_json(run_dir / "build-manifest.json")
    if manifest.get("schema_version") != 1 or manifest.get("milestone") != MILESTONE:
        raise ValidationError("M05 build manifest identity is invalid")
    if manifest.get("specification_sha256") != sha256_file(root / SPEC_RELATIVE):
        raise ValidationError("M05 build manifest specification identity differs")
    if manifest.get("specification_schema_sha256") != sha256_file(root / SCHEMA_RELATIVE):
        raise ValidationError("M05 build manifest schema identity differs")
    if manifest.get("consumed_identities") != spec["consumed_identities"] or manifest.get("derived_layout") != derived:
        raise ValidationError("M05 build manifest contract data differs")
    if manifest.get("inputs") != [serializable_record(record) for record in records]:
        raise ValidationError("M05 build manifest input identities differ")
    raw_path = run_dir / spec["image"]["raw_filename"]
    d88_path = run_dir / spec["image"]["d88_filename"]
    if manifest.get("raw") != file_identity(raw_path):
        raise ValidationError("M05 raw image identity differs from its build manifest")
    d88_expected = {
        **file_identity(d88_path),
        "populated_tracks": spec["d88"]["populated_tracks"],
        "sector_count": derived["total_sectors"],
    }
    if manifest.get("d88") != d88_expected:
        raise ValidationError("M05 D88 identity differs from its build manifest")
    expected_builder = {
        "build_media.py": sha256_file(root / "tools/m05/build_media.py"),
        "common.py": sha256_file(root / "tools/m05/common.py"),
    }
    if manifest.get("builder_identities") != expected_builder:
        raise ValidationError("M05 builder identity differs")
    if any(manifest.get("claims", {}).values()):
        raise ValidationError("M05 build manifest makes a forbidden boot, runtime, VAEG, or hardware claim")
    return manifest


def verify_run(root: Path, run_dir: Path, spec: dict, derived: dict, records: list[dict]) -> dict:
    build = verify_build_manifest(root, run_dir, spec, derived, records)
    actual_inspection = load_canonical_json(run_dir / "inspection-manifest.json")
    expected_inspection = inspect_run(root, run_dir, False)
    if actual_inspection != expected_inspection:
        raise ValidationError("M05 inspection manifest does not match a fresh independent inspection")
    raw_path = run_dir / spec["image"]["raw_filename"]
    reconstructed = run_dir / "extracted-raw.img"
    if reconstructed.read_bytes() != raw_path.read_bytes():
        raise ValidationError("stored D88 extraction differs from the canonical raw image")
    expected_names = {record["dos_name"] for record in records}
    extracted_dir = run_dir / "extracted"
    actual_names = {path.name for path in extracted_dir.iterdir() if path.is_file()}
    if actual_names != expected_names or any(path.is_symlink() for path in extracted_dir.iterdir()):
        raise ValidationError("stored extracted payload set differs")
    for record in records:
        path = extracted_dir / record["dos_name"]
        if file_identity(path) != {"sha256": record["sha256"], "size": record["size"]}:
            raise ValidationError(f"stored extracted payload identity differs: {record['dos_name']}")
    expected_paths = {
        spec["image"]["raw_filename"],
        spec["image"]["d88_filename"],
        "build-manifest.json",
        "inspection-manifest.json",
        "extracted-raw.img",
        "extracted",
        *(f"extracted/{name}" for name in expected_names),
    }
    snapshot = tree_snapshot(run_dir)
    if {item["path"] for item in snapshot} != expected_paths:
        raise ValidationError("M05 run contains missing or unexpected output paths")
    build_regions = build["regions"]
    inspected_regions = actual_inspection["regions"]
    for key in ("fat_1", "fat_2", "root_directory"):
        if build_regions[key] != inspected_regions[key]:
            raise ValidationError(f"builder and inspector region identity differ: {key}")
    if build_regions["boot_record"] != {key: inspected_regions["boot_record"][key] for key in ("sha256", "size")}:
        raise ValidationError("builder and inspector boot-record identity differ")
    if build_regions["allocations"] != inspected_regions["allocations"]:
        raise ValidationError("builder and inspector allocation maps differ")
    return {
        "build_manifest": build,
        "files": snapshot,
        "inspection_manifest": actual_inspection,
        "milestone": MILESTONE,
        "schema_version": 1,
    }


def check_comparison(root: Path, run1: Path, run2: Path) -> None:
    path = root / RESULTS_RELATIVE / "comparison.json"
    recorded = load_canonical_json(path)
    recomputed = compare_runs(run1, run2)
    if recorded != recomputed or recorded.get("status") != "pass" or recorded.get("byte_identical") is not True:
        raise ValidationError("M05 comparison is missing, stale, or not byte-identical")


def verify_or_enroll(root: Path, enroll: bool) -> str:
    spec, derived, records = preflight(root)
    run1 = root / RESULTS_RELATIVE / "run-1"
    run2 = root / RESULTS_RELATIVE / "run-2"
    check_comparison(root, run1, run2)
    first = verify_run(root, run1, spec, derived, records)
    second = verify_run(root, run2, spec, derived, records)
    if first != second:
        raise ValidationError("M05 run snapshots differ after independent verification")
    golden_path = root / GOLDEN_RELATIVE
    if enroll:
        if golden_path.exists():
            raise ValidationError("M05 golden already exists; ordinary enrollment never overwrites it")
        write_canonical_json(golden_path, first)
        print(f"M05 golden enrolled explicitly: {sha256_file(golden_path)}")
    else:
        golden = load_canonical_json(golden_path)
        if golden != first:
            raise ValidationError("M05 result does not match the committed textual golden manifest")
        print(f"M05 verification passed: golden={sha256_file(golden_path)}")
    return sha256_file(golden_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight", action="store_true")
    modes.add_argument("--clean", action="store_true")
    modes.add_argument("--verify", action="store_true")
    modes.add_argument("--enroll-golden", action="store_true")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.repo_root.resolve()
    try:
        if args.clean:
            remove_owned_results(root)
            print("M05 generated result path cleaned")
        elif args.preflight:
            preflight(root)
        else:
            verify_or_enroll(root, args.enroll_golden)
    except (OSError, OverflowError, ValueError, ValidationError) as exc:
        print(f"M05 verification failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
