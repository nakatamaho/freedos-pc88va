#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Verify the public M07R2 Class A record and optional local private gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATUS_PATH = ROOT / "config/m07/m07r2-public-status.json"
SCHEMA_PATH = ROOT / "schema/m07r2-public-status.schema.json"
GOLDEN_PATH = ROOT / "qa/golden/m07r2-public-status.sha256"
PRIVATE_WORK = ROOT / "results/m07r2-private"
START_COMMIT = "93d88d047159364669975dd95c45ace7531a935b"
VAEG_COMMIT = "16ad2e0619bf4ed82a739325f7291eba4a6ed8ad"
EXPECTED_GITLINKS = {
    "components/fdkernel": "69ccdd8699895722fc537d647ec490685532bdc4",
    "components/freecom": "855281a3114b43ad4b8d9a320f2aca39be046bba",
    "components/country": "23f189cca3420606eae8723884fa92ccd65eb307",
}
EXPECTED_IDENTITIES = {
    "m07r1_status": ("config/m07/m07r1-public-status.json", "768b1bde31015b8920d43db1a7822efa98797dda805fc0a4cb6d2c71936c3f69"),
    "m07r1_schema": ("schema/m07r1-public-status.schema.json", "e0a1ae543d4af9e9c70f1ee1de44d0fadfca50838651fc3105c86b36fdbe1f4e"),
    "probe_source": ("tools/m07/probe.asm", "ae17a5dcd461e80b2a0ca6db73333eebb461d81a0bb9589e464731c4f5bdfa7b"),
    "variants": ("config/m07/variants.json", "fdc75b8353c2d1c8a858a86cbabd47eecd6327133c47184c8606f00c4a62768e"),
    "public_result_schema": ("schema/m07-public-result.schema.json", "4a314a29b243660d9fe796811cfe62f8799646551c4c53a08b410cb01c9fdc73"),
    "private_overlay_schema": ("schema/m07-private-overlay.schema.json", "e4b6e3eb67280e197c89f142e4e4d29ddc1705476eaebc868839e79de4c7e2a4"),
    "public_golden": ("qa/golden/m07-probe-manifest.json", "fb7637082efeb2d4f57437d723d22453b6493904b7d3e805230e6d00d93aeadd"),
}
EXPECTED_FIELDS = {
    "accepted_signature_profile",
    "boot_drive_identity",
    "firmware_attempts_m05_geometry",
    "first_cs_ip",
    "initial_register_state",
    "initial_sector_reads",
    "loaded_extent",
    "physical_load_address",
}
PUBLIC_FILES = (
    "config/m07/m07r2-public-status.json",
    "schema/m07r2-public-status.schema.json",
    "docs/porting/m07r2-positive-control-diagnosis.md",
    "tools/m07r2/d88.py",
    "tools/m07r2/trace_boundaries.py",
    "tools/m07r2/verify_m07r2.py",
    "tests/m07r2/test_m07r2.py",
    "qa/golden/m07r2-public-status.sha256",
    ".github/workflows/m07-probe.yml",
    "Makefile",
)


class M07R2Error(RuntimeError):
    """A public or local-only M07R2 invariant failed."""


def run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=ROOT, check=False, capture_output=True, text=True)
    if check and result.returncode:
        raise M07R2Error("command failed during M07R2 verification")
    return result


def git(*args: str, check: bool = True) -> str:
    return run(["git", *args], check=check).stdout


def sha256(path: Path) -> str:
    if not path.is_file() or path.is_symlink() or path.stat().st_nlink != 1:
        raise M07R2Error(f"unsafe or missing regular file: {path.relative_to(ROOT)}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def load_canonical(path: Path) -> object:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise M07R2Error(f"cannot parse JSON: {path.relative_to(ROOT)}") from exc
    if path.read_bytes() != canonical_bytes(value):
        raise M07R2Error(f"JSON is not canonical: {path.relative_to(ROOT)}")
    return value


def validate_schema(value: object, schema: dict, location: str = "$") -> None:
    expected_type = schema.get("type")
    type_map = {"object": dict, "array": list, "string": str, "integer": int, "boolean": bool}
    if expected_type in type_map and not isinstance(value, type_map[expected_type]):
        raise M07R2Error(f"schema type mismatch at {location}")
    if "const" in schema and value != schema["const"]:
        raise M07R2Error(f"schema constant mismatch at {location}")
    if "enum" in schema and value not in schema["enum"]:
        raise M07R2Error(f"schema enumeration mismatch at {location}")
    if isinstance(value, dict):
        required = schema.get("required", [])
        if any(key not in value for key in required):
            raise M07R2Error(f"schema required property missing at {location}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False and set(value) - set(properties):
            raise M07R2Error(f"schema additional property at {location}")
        for key, child in value.items():
            if key in properties:
                validate_schema(child, properties[key], f"{location}.{key}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", len(value)):
            raise M07R2Error(f"schema array length mismatch at {location}")
        if schema.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
            raise M07R2Error(f"schema array duplicates at {location}")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                validate_schema(item, item_schema, f"{location}[{index}]")


def validate_components() -> None:
    for relative, expected in EXPECTED_GITLINKS.items():
        actual = git("rev-parse", f"HEAD:{relative}").strip()
        if actual != expected:
            raise M07R2Error(f"component gitlink differs: {relative}")
        if git("-C", relative, "status", "--porcelain=v1", "--untracked-files=all"):
            raise M07R2Error(f"component worktree is not clean: {relative}")


def validate_staging() -> None:
    forbidden_suffixes = {".rom", ".d88", ".img", ".bin", ".log", ".trace", ".zip", ".tar", ".gz"}
    for relative in git("diff", "--cached", "--name-only", "-z").split("\0"):
        if not relative:
            continue
        lowered = relative.lower()
        if Path(lowered).suffix in forbidden_suffixes or "private" in lowered or lowered.startswith("components/"):
            raise M07R2Error("private, generated, or component content is staged")


def forbidden_public_markers() -> tuple[str, ...]:
    return (
        "/" + "Users" + "/",
        "/" + "home" + "/",
        "file:" + "//",
        "pc88va-" + "private-docs",
        "rom_" + "basename",
        "disk_" + "name",
        "sector_" + "dump",
        "trace_" + "address",
    )


def validate_public_payload(text: str) -> None:
    if any(token.lower() in text.lower() for token in forbidden_public_markers()):
        raise M07R2Error("public text contains a private-data marker")


def validate_public_text() -> None:
    for relative in PUBLIC_FILES:
        path = ROOT / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        try:
            validate_public_payload(text)
        except M07R2Error as exc:
            raise M07R2Error(f"public M07R2 file contains a private-data marker: {relative}") from exc


def verify_public() -> None:
    head = git("rev-parse", "HEAD").strip()
    if run(["git", "merge-base", "--is-ancestor", START_COMMIT, head], check=False).returncode:
        raise M07R2Error("current branch does not descend from the fixed M07R1 commit")
    for name, (relative, expected) in EXPECTED_IDENTITIES.items():
        if sha256(ROOT / relative) != expected:
            raise M07R2Error(f"accepted identity differs: {name}")
    status = load_canonical(STATUS_PATH)
    schema = load_canonical(SCHEMA_PATH)
    if not isinstance(status, dict) or not isinstance(schema, dict):
        raise M07R2Error("public status or schema root is not an object")
    validate_schema(status, schema)
    if status["vaeg"]["commit"] != VAEG_COMMIT:
        raise M07R2Error("VAEG fixed commit differs")
    gate = status["private_gate"]
    if set(gate["unresolved_fields"]) != EXPECTED_FIELDS or gate["resolved_fields"]:
        raise M07R2Error("M07R2 mandatory field disposition differs")
    if gate["control_established"] or gate["probe_variant_trial_count"] or gate["adaptive_variant_count"]:
        raise M07R2Error("Class A status contains post-control experimentation")
    expected_digest = GOLDEN_PATH.read_text(encoding="ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{64}", expected_digest) or expected_digest != sha256(STATUS_PATH):
        raise M07R2Error("M07R2 public status digest differs")
    validate_components()
    validate_staging()
    validate_public_text()
    print(f"M07R2 public verification passed: status={expected_digest}")


def private_tokens(state: dict) -> set[str]:
    tokens = {str(state.get("private_root", "")), str(state.get("rom_dir", ""))}
    for candidate in state.get("candidates", []):
        for key in ("path", "relative_path"):
            tokens.add(str(candidate.get(key, "")))
        d88 = candidate.get("d88", {})
        tokens.add(str(d88.get("sha256", "")))
    rom_dir = Path(state["rom_dir"])
    if rom_dir.is_dir():
        for path in rom_dir.rglob("*"):
            if path.is_file():
                tokens.update((path.name, str(path.resolve()), hashlib.sha256(path.read_bytes()).hexdigest()))
    return {token for token in tokens if len(token) >= 8}


def verify_private() -> None:
    state_path = PRIVATE_WORK / "evidence/private-state.json"
    summary_path = PRIVATE_WORK / "evidence/control-summary.json"
    first_projection = PRIVATE_WORK / "trials/CONTROL/run-1/projection.json"
    second_projection = PRIVATE_WORK / "trials/CONTROL/run-2/projection.json"
    for path in (state_path, summary_path, first_projection, second_projection):
        if not path.is_file():
            raise M07R2Error("required ignored private evidence is absent")
        if run(["git", "check-ignore", "-q", str(path.relative_to(ROOT))], check=False).returncode:
            raise M07R2Error("private evidence path is not ignored")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    expected = {
        "control_attempted": True,
        "control_established": False,
        "control_repeated": True,
        "input_preservation": "passed",
        "marker_reached": False,
        "promotion_status": "prohibited_pending_user_approval",
        "schema_version": 1,
        "trial_count": 2,
    }
    if any(summary.get(key) != value for key, value in expected.items()):
        raise M07R2Error("private Class A summary differs from the public redaction")
    if first_projection.read_bytes() != second_projection.read_bytes():
        raise M07R2Error("private repeated projections differ")
    tracked = set(PUBLIC_FILES)
    tracked.update(git("diff", "--name-only", START_COMMIT, "--").splitlines())
    tracked.update(git("diff", "--cached", "--name-only").splitlines())
    needles = private_tokens(state)
    for relative in sorted(tracked):
        if not relative:
            continue
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            continue
        data = path.read_bytes()
        if b"\0" in data:
            continue
        text = data.decode("utf-8", errors="ignore")
        if any(token in text for token in needles):
            raise M07R2Error("tracked content contains a private identity")
    print("M07R2 local private-evidence gate passed without exposing private values")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-evidence", action="store_true")
    args = parser.parse_args()
    try:
        if args.private_evidence:
            verify_private()
        else:
            verify_public()
    except (M07R2Error, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"M07R2 verification failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
