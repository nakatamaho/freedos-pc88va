#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Verify the abstract public M07R4 reconstruction status."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATUS = ROOT / "config/m07/m07r4-public-status.json"
SCHEMA = ROOT / "schema/m07r4-public-status.schema.json"
GOLDEN = ROOT / "qa/golden/m07r4-public-status.sha256"
START_COMMIT = "75997715f6f0193266d63f6617a4308d3520f6d4"
VAEG_COMMIT = "16ad2e0619bf4ed82a739325f7291eba4a6ed8ad"
COMPONENTS = {
    "components/fdkernel": "69ccdd8699895722fc537d647ec490685532bdc4",
    "components/freecom": "855281a3114b43ad4b8d9a320f2aca39be046bba",
    "components/country": "23f189cca3420606eae8723884fa92ccd65eb307",
}
PRIOR_IDENTITIES = {
    "config/m07/m07r3-public-status.json": "ee4f8bc3040a2c900344c3dd25595a0acf65ad6e9d7a9040ae931ebdde20d156",
    "schema/m07r3-public-status.schema.json": "339da36bb6e5aa5b56438625592df9bacf0d8dab028c274bd216015ea702cc45",
    "tools/m07/probe.asm": "ae17a5dcd461e80b2a0ca6db73333eebb461d81a0bb9589e464731c4f5bdfa7b",
    "config/m07/variants.json": "fdc75b8353c2d1c8a858a86cbabd47eecd6327133c47184c8606f00c4a62768e",
}
FIELDS = {
    "accepted_signature_profile",
    "boot_drive_identity",
    "entry_cs_ip",
    "firmware_attempts_m05_geometry",
    "initial_load_extent",
    "initial_register_state",
    "initial_sector_reads",
    "physical_load_address",
}
PUBLIC_FILES = (
    STATUS,
    SCHEMA,
    ROOT / "docs/porting/m07r4-rom-d88-reconstruction.md",
    ROOT / ".github/workflows/m07r4-boot-reconstruction.yml",
    ROOT / "Makefile",
)
FORBIDDEN = (
    "pc88va-private-docs",
    "rom_basename",
    "rom_sha256",
    "disk_name",
    "sector_dump",
    "trace_excerpt",
    "winning_variant",
    "private_overlay",
)


class VerificationError(RuntimeError):
    """Raised when an M07R4 public invariant fails."""


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_canonical(path: Path) -> object:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"cannot parse JSON: {path}") from exc
    if path.read_bytes() != canonical(value):
        raise VerificationError(f"JSON is not canonical: {path}")
    return value


def validate_schema(value: object, schema: dict, location: str = "$") -> None:
    types = {"object": dict, "array": list, "string": str, "integer": int, "boolean": bool}
    expected = schema.get("type")
    if expected in types and (not isinstance(value, types[expected]) or expected == "integer" and isinstance(value, bool)):
        raise VerificationError(f"schema type mismatch at {location}")
    if "const" in schema and value != schema["const"]:
        raise VerificationError(f"schema constant mismatch at {location}")
    if "pattern" in schema and (not isinstance(value, str) or re.fullmatch(schema["pattern"], value) is None):
        raise VerificationError(f"schema pattern mismatch at {location}")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False and set(value) - set(properties):
            raise VerificationError(f"schema additional property at {location}")
        for key in schema.get("required", []):
            if key not in value:
                raise VerificationError(f"schema required property missing at {location}")
        for key, child in value.items():
            if key in properties:
                validate_schema(child, properties[key], f"{location}.{key}")
    elif isinstance(value, list):
        if "const" not in schema and not (schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", len(value))):
            raise VerificationError(f"schema array length mismatch at {location}")
        if schema.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
            raise VerificationError(f"schema array duplicates at {location}")
        if isinstance(schema.get("items"), dict):
            for index, child in enumerate(value):
                validate_schema(child, schema["items"], f"{location}[{index}]")


def git(*args: str, cwd: Path = ROOT, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    if check and result.returncode:
        raise VerificationError(f"git command failed: {' '.join(args)}")
    return result.stdout


def validate_components() -> None:
    for relative, expected in COMPONENTS.items():
        if git("rev-parse", f"HEAD:{relative}").strip() != expected:
            raise VerificationError(f"component gitlink differs: {relative}")
        if git("status", "--short", "--untracked-files=all", cwd=ROOT / relative):
            raise VerificationError(f"component worktree is dirty: {relative}")


def reject_public_text(text: str) -> None:
    lowered = text.lower()
    if any(marker in lowered for marker in FORBIDDEN):
        raise VerificationError("public M07R4 output contains a private-data marker")
    if re.search(r"(?i)(?:^|[^a-z])/(?:users|home)/", text):
        raise VerificationError("public M07R4 output contains an absolute host path")


def validate_status(data: dict) -> None:
    if data.get("status") != "M07R4 BLOCKED — B2 PREDICATE NOT DISTINGUISHABLE":
        raise VerificationError("M07R4 status is not the bounded UNKNOWN result")
    if data.get("classification") != "UNKNOWN":
        raise VerificationError("M07R4 classification is not UNKNOWN")
    if data.get("boundaries", {}).get("last_reached") != "B1" or data.get("boundaries", {}).get("first_unobserved") != "B2":
        raise VerificationError("M07R4 boundary disposition differs")
    fields = data.get("fields", {})
    if set(fields.get("unresolved", [])) != FIELDS or fields.get("resolved") or fields.get("resolved_count") != 0:
        raise VerificationError("M07R4 mandatory field disposition differs")
    if data.get("fields", {}).get("promotion_status") != "prohibited_pending_user_approval":
        raise VerificationError("M07R4 promotion status is unsafe")
    if data.get("private_gate", {}).get("concrete_values_published") is not False:
        raise VerificationError("private values are marked as public")
    if data.get("vaeg", {}).get("commit") != VAEG_COMMIT or data.get("vaeg", {}).get("source_changed") is not False:
        raise VerificationError("fixed VAEG identity or source-change status differs")
    reconstruction = data.get("reconstruction", {})
    if reconstruction.get("marker_reached") or reconstruction.get("marker_repeat_count") != 0:
        raise VerificationError("M07R4 cannot claim marker execution")
    if reconstruction.get("b2_blocker_category") != "UNKNOWN":
        raise VerificationError("M07R4 B2 category is overclaimed")


def validate_prior_identities() -> None:
    head = git("rev-parse", "HEAD").strip()
    if subprocess.run(["git", "merge-base", "--is-ancestor", START_COMMIT, head], cwd=ROOT, check=False).returncode:
        raise VerificationError("M07R4 branch does not descend from the accepted M07R3 commit")
    for relative, expected in PRIOR_IDENTITIES.items():
        if sha256(ROOT / relative) != expected:
            raise VerificationError(f"accepted M07R3 identity changed: {relative}")


def validate_safety() -> None:
    for relative in git("ls-files", "-z").split("\0"):
        if not relative:
            continue
        path = ROOT / relative
        if path.suffix.lower() in {".rom", ".d88", ".img", ".bin", ".exe", ".trace", ".log"}:
            raise VerificationError(f"generated/private artifact is tracked: {relative}")
    for path in PUBLIC_FILES:
        if path.is_file():
            reject_public_text(path.read_text(encoding="utf-8", errors="ignore"))
    if "components/" in git("diff", "--cached", "--name-only"):
        raise VerificationError("component change is staged")


def verify() -> None:
    status = load_canonical(STATUS)
    schema = load_canonical(SCHEMA)
    if not isinstance(status, dict) or not isinstance(schema, dict):
        raise VerificationError("M07R4 status or schema root is not an object")
    validate_schema(status, schema)
    validate_status(status)
    validate_prior_identities()
    validate_components()
    if GOLDEN.read_text(encoding="ascii").strip() != sha256(STATUS):
        raise VerificationError("M07R4 status golden is stale")
    validate_safety()
    print("M07R4 public verification passed: abstract B2 reconstruction record")


if __name__ == "__main__":
    try:
        verify()
    except (VerificationError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"M07R4 ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
