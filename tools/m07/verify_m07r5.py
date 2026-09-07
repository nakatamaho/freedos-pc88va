#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Verify the abstract public M07R5 firmware request-gate record."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATUS = ROOT / "config/m07/m07r5-public-status.json"
SCHEMA = ROOT / "schema/m07r5-public-status.schema.json"
GOLDEN = ROOT / "qa/golden/m07r5-public-status.sha256"
START_COMMIT = "abcea71317a8813c6c294ec7f27856aba400e0dd"
VAEG_COMMIT = "6bdaae109c92d26a65f0b0b1a9a50eeae5c1385a"
COMPONENTS = {
    "components/fdkernel": "69ccdd8699895722fc537d647ec490685532bdc4",
    "components/freecom": "855281a3114b43ad4b8d9a320f2aca39be046bba",
    "components/country": "23f189cca3420606eae8723884fa92ccd65eb307",
}
PRIOR_IDENTITIES = {
    "config/m07/m07r4-public-status.json": "e572fbf6f28d1330223cf13e7c7c8df4b7b1b4b56d9af7f6b77e09983078f4be",
    "schema/m07r4-public-status.schema.json": "e8dffd3d09efcd1cd9f4fcbb81e2aa733041ef2c4f66728f56d1c154833b1a2d",
    "config/m07/m07r3-public-status.json": "ee4f8bc3040a2c900344c3dd25595a0acf65ad6e9d7a9040ae931ebdde20d156",
    "schema/m07r3-public-status.schema.json": "339da36bb6e5aa5b56438625592df9bacf0d8dab028c274bd216015ea702cc45",
    "tools/m07/probe.asm": "ae17a5dcd461e80b2a0ca6db73333eebb461d81a0bb9589e464731c4f5bdfa7b",
    "config/m07/variants.json": "fdc75b8353c2d1c8a858a86cbabd47eecd6327133c47184c8606f00c4a62768e",
    "schema/m07-public-result.schema.json": "4a314a29b243660d9fe796811cfe62f8799646551c4c53a08b410cb01c9fdc73",
    "schema/m07-private-overlay.schema.json": "e4b6e3eb67280e197c89f142e4e4d29ddc1705476eaebc868839e79de4c7e2a4",
    "qa/golden/m07-probe-manifest.json": "fb7637082efeb2d4f57437d723d22453b6493904b7d3e805230e6d00d93aeadd",
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
    ROOT / "docs/porting/m07r5-firmware-no-request-gate.md",
    ROOT / ".github/workflows/m07r5-firmware-request-gate.yml",
    ROOT / "Makefile",
)
FORBIDDEN = (
    "pc88va-private-docs",
    "file://",
    "rom_basename",
    "rom_sha256",
    "disk_name",
    "sector_dump",
    "trace_excerpt",
    "winning_variant",
    "private_overlay",
    "private-result",
    "concrete_address",
)


class VerificationError(RuntimeError):
    """Raised when an M07R5 public invariant fails."""


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_canonical(path: Path) -> object:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"cannot parse JSON: {path}") from exc
    if path.read_bytes() != canonical(data):
        raise VerificationError(f"JSON is not canonical: {path}")
    return data


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
    elif isinstance(value, list) and isinstance(schema.get("items"), dict):
        for index, child in enumerate(value):
            validate_schema(child, schema["items"], f"{location}[{index}]")


def git(*args: str, cwd: Path = ROOT) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode:
        raise VerificationError(f"git command failed: {' '.join(args)}")
    return result.stdout


def reject_public_text(text: str) -> None:
    lowered = text.lower()
    if any(marker in lowered for marker in FORBIDDEN):
        raise VerificationError("public M07R5 output contains private or concrete observation material")
    if re.search(r"(?i)\b(?:physical_load_address|entry_cs_ip|load_address|first_cs_ip)\s*[:=]\s*(?:0x[0-9a-f]+|[0-9a-f]+:[0-9a-f]+|[0-9]+)", text):
        raise VerificationError("public M07R5 output contains a concrete address")
    if re.search(r"(?i)(?:^|[^a-z])/(?:users|home)/", text):
        raise VerificationError("public M07R5 output contains an absolute host path")


def validate_components() -> None:
    for relative, expected in COMPONENTS.items():
        stage = git("ls-files", "--stage", "--", relative).split()
        if len(stage) < 2 or stage[0] != "160000" or stage[1] != expected:
            raise VerificationError(f"component gitlink drift: {relative}")
        if git("rev-parse", "HEAD", cwd=ROOT / relative).strip() != expected:
            raise VerificationError(f"component checkout drift: {relative}")
        if git("status", "--short", "--untracked-files=all", cwd=ROOT / relative):
            raise VerificationError(f"component worktree is dirty: {relative}")


def validate_prior_identities() -> None:
    head = git("rev-parse", "HEAD").strip()
    if subprocess.run(["git", "merge-base", "--is-ancestor", START_COMMIT, head], cwd=ROOT, check=False).returncode:
        raise VerificationError("M07R5 branch does not descend from accepted M07R4")
    for relative, expected in PRIOR_IDENTITIES.items():
        if digest(ROOT / relative) != expected:
            raise VerificationError(f"accepted public identity changed: {relative}")


def validate_status(data: dict) -> None:
    if data.get("status") != "M07R5 BLOCKED — FIRMWARE PREDICATE PRODUCER UNOBSERVABLE":
        raise VerificationError("M07R5 status is not the bounded blocked result")
    if data.get("classification") != "HANDSHAKE_INIT":
        raise VerificationError("M07R5 predicate category differs")
    if data.get("irq", {}).get("classification") != "NONCAUSAL_IRQ":
        raise VerificationError("M07R5 IRQ causality classification differs")
    boundaries = data.get("boundaries", {})
    if boundaries.get("last_reached") != "B2" or boundaries.get("first_blocked") != "B3":
        raise VerificationError("M07R5 boundary disposition differs")
    if set(data.get("fields", {}).get("unresolved", [])) != FIELDS or data["fields"].get("resolved") or data["fields"].get("resolved_count") != 0:
        raise VerificationError("M07R5 mandatory field disposition differs")
    if data.get("predicate", {}).get("producer_fully_identified") is not False:
        raise VerificationError("M07R5 overclaims predicate producer identification")
    if data.get("trial_summary", {}).get("evidence_backed_changed_predicate_trials") != 0:
        raise VerificationError("M07R5 reports an unrecorded predicate trial")
    private_gate = data.get("private_gate", {})
    if private_gate.get("concrete_values_published") is not False or private_gate.get("projection_determinism") != "byte-identical":
        raise VerificationError("M07R5 private gate is unsafe or nondeterministic")
    vaeg = data.get("vaeg", {})
    if vaeg.get("commit") != VAEG_COMMIT or vaeg.get("production_memory") is not True or vaeg.get("tests_disabled") is not True:
        raise VerificationError("accepted VAEG causal-trace capability differs")


def validate_safety() -> None:
    for relative in (item for item in git("ls-files", "-z").split("\0") if item):
        path = ROOT / relative
        if path.suffix.lower() in {".rom", ".d88", ".img", ".bin", ".exe", ".trace", ".log"}:
            raise VerificationError(f"private/generated artifact is tracked: {relative}")
    for path in PUBLIC_FILES:
        if path.is_file():
            reject_public_text(path.read_text(encoding="utf-8", errors="ignore"))
    if subprocess.run(["git", "check-ignore", "-q", "results/m07r5-private"], cwd=ROOT, check=False).returncode:
        raise VerificationError("private M07R5 results directory is not ignored")
    if "components/" in git("diff", "--cached", "--name-only"):
        raise VerificationError("component change is staged")


def verify() -> None:
    status = load_canonical(STATUS)
    schema = load_canonical(SCHEMA)
    if not isinstance(status, dict) or not isinstance(schema, dict):
        raise VerificationError("M07R5 status or schema root is not an object")
    validate_schema(status, schema)
    validate_status(status)
    validate_prior_identities()
    validate_components()
    if GOLDEN.read_text(encoding="ascii").strip() != digest(STATUS):
        raise VerificationError("M07R5 status golden is stale")
    validate_safety()
    print("M07R5 public verification passed: abstract handshake-init blocked record")


if __name__ == "__main__":
    try:
        verify()
    except (VerificationError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"M07R5 ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
