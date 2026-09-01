#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Verify the public, abstract M07R3 FDD boot-path diagnosis record."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATUS = ROOT / "config/m07/m07r3-public-status.json"
SCHEMA = ROOT / "schema/m07r3-public-status.schema.json"
GOLDEN = ROOT / "qa/golden/m07r3-public-status.sha256"
QUESTION_FIELDS = {
    "accepted_signature_profile",
    "boot_drive_identity",
    "entry_cs_ip",
    "firmware_attempts_m05_geometry",
    "initial_load_extent",
    "initial_register_state",
    "initial_sector_reads",
    "physical_load_address",
}
COMPONENTS = {
    "components/fdkernel": "69ccdd8699895722fc537d647ec490685532bdc4",
    "components/freecom": "855281a3114b43ad4b8d9a320f2aca39be046bba",
    "components/country": "23f189cca3420606eae8723884fa92ccd65eb307",
}
PUBLIC_IDENTITIES = {
    "config/m07/m07r2-public-status.json": "a1c7a30cac60b5e725b21dec98f79d1f5fb08881c37efcae509d2ac44e7a538b",
    "schema/m07r2-public-status.schema.json": "fc0ca205d3fdbb8f30c7cc7c7e45f037d32429ceb4e6f36b105ee40397d9767f",
    "tools/m07/probe.asm": "ae17a5dcd461e80b2a0ca6db73333eebb461d81a0bb9589e464731c4f5bdfa7b",
    "config/m07/variants.json": "fdc75b8353c2d1c8a858a86cbabd47eecd6327133c47184c8606f00c4a62768e",
    "schema/m07-public-result.schema.json": "4a314a29b243660d9fe796811cfe62f8799646551c4c53a08b410cb01c9fdc73",
    "schema/m07-private-overlay.schema.json": "e4b6e3eb67280e197c89f142e4e4d29ddc1705476eaebc868839e79de4c7e2a4",
    "qa/golden/m07-probe-manifest.json": "fb7637082efeb2d4f57437d723d22453b6493904b7d3e805230e6d00d93aeadd",
}
FORBIDDEN = (
    "/users/",
    "file://",
    "pc88va-" + "private-docs",
    "rom_basename",
    "rom_sha256",
    "disk_name",
    "sector_dump",
    "trace_excerpt",
    "winning_variant",
)


class M07R3Error(RuntimeError):
    """Raised when a public M07R3 invariant fails."""


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise M07R3Error(f"cannot parse JSON: {path}") from exc
    if canonical(data) != path.read_bytes():
        raise M07R3Error(f"JSON is not canonical: {path}")
    return data


def git(*args: str, cwd: Path = ROOT) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode:
        raise M07R3Error(f"git command failed: {' '.join(args)}")
    return result.stdout


def reject_private_text(text: str) -> None:
    lowered = text.lower()
    if any(marker in lowered for marker in FORBIDDEN):
        raise M07R3Error("public M07R3 data contains private or concrete observation material")


def validate_components() -> None:
    for path, expected in COMPONENTS.items():
        stage = git("ls-files", "--stage", "--", path).split()
        if len(stage) < 2 or stage[0] != "160000" or stage[1] != expected:
            raise M07R3Error(f"component gitlink drift: {path}")
        component = ROOT / path
        if git("rev-parse", "HEAD", cwd=component).strip() != expected:
            raise M07R3Error(f"component checkout drift: {path}")
        if git("status", "--short", "--untracked-files=all", cwd=component):
            raise M07R3Error(f"component worktree is dirty: {path}")


def validate_public_identities() -> None:
    for relative, expected in PUBLIC_IDENTITIES.items():
        path = ROOT / relative
        if digest(path) != expected:
            raise M07R3Error(f"accepted public identity changed: {relative}")


def validate_status(data: dict) -> None:
    if data.get("schema_version") != 1 or data.get("milestone") != "M07R3":
        raise M07R3Error("M07R3 status identity is invalid")
    if data.get("classification") != "U":
        raise M07R3Error("M07R3 classification is not the unresolved-control result")
    comparison = data.get("comparison", {})
    if comparison.get("last_common_boundary") != "B1" or comparison.get("first_unobserved_boundary") != "B2":
        raise M07R3Error("M07R3 boundary result differs")
    if comparison.get("paired_projection_result") != "byte-identical":
        raise M07R3Error("M07R3 repeated projections are not deterministic")
    if data.get("m08", {}).get("mandatory_resolved_count") != 0:
        raise M07R3Error("M07R3 must not resolve an M08 field")
    if set(data.get("m08", {}).get("mandatory_unresolved_fields", [])) != QUESTION_FIELDS:
        raise M07R3Error("M07R3 M08 question set differs")
    if data.get("m07r2", {}).get("resumed") is not False:
        raise M07R3Error("M07R2 was resumed without a positive control")
    if data.get("private_gate", {}).get("concrete_values_published") is not False:
        raise M07R3Error("private values are marked as published")
    if data.get("vaeg", {}).get("commit") != "16ad2e0619bf4ed82a739325f7291eba4a6ed8ad":
        raise M07R3Error("fixed VAEG commit differs")


def validate_safety() -> None:
    tracked = [item for item in git("ls-files", "-z").split("\0") if item]
    for relative in tracked:
        path = ROOT / relative
        if not path.is_file():
            continue
        if path.suffix.lower() in {".rom", ".d88", ".img", ".bin", ".exe", ".trace", ".log"}:
            raise M07R3Error(f"generated/private artifact is tracked: {relative}")
    public_files = (
        STATUS,
        SCHEMA,
        ROOT / "docs/porting/m07r3-vaeg-fdd-boot-path-establishment.md",
        ROOT / ".github/workflows/m07r3-fdd-boot-path.yml",
        ROOT / "Makefile",
    )
    for path in public_files:
        reject_private_text(path.read_text(encoding="utf-8", errors="ignore"))
    if "components/" in git("diff", "--cached", "--name-only"):
        raise M07R3Error("component change is staged")


def verify() -> None:
    status = load_json(STATUS)
    load_json(SCHEMA)
    validate_status(status)
    validate_components()
    validate_public_identities()
    expected_golden = GOLDEN.read_text(encoding="ascii").strip()
    if expected_golden != digest(STATUS):
        raise M07R3Error("M07R3 status golden is stale")
    validate_safety()
    print("M07R3 public verification passed: abstract unresolved-control record")


if __name__ == "__main__":
    try:
        verify()
    except (M07R3Error, OSError, UnicodeError) as exc:
        print(f"M07R3 ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
