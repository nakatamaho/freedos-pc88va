#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Verify the abstract public M07R6 subsystem command-gate record."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATUS = ROOT / "config/m07/m07r6-public-status.json"
SCHEMA = ROOT / "schema/m07r6-public-status.schema.json"
GOLDEN = ROOT / "qa/golden/m07r6-public-status.sha256"
START_COMMIT = "7dcf0edaedc17379f4d60f0a1c814af9bf9be854"
VAEG_COMMIT = "6bdaae109c92d26a65f0b0b1a9a50eeae5c1385a"
COMPONENTS = {
    "components/fdkernel": "69ccdd8699895722fc537d647ec490685532bdc4",
    "components/freecom": "855281a3114b43ad4b8d9a320f2aca39be046bba",
    "components/country": "23f189cca3420606eae8723884fa92ccd65eb307",
}
PRIOR_IDENTITIES = {
    "config/m07/m07r5-public-status.json": "60f8254ed2bef023bff3daa00c8cd6caa9094beda6ec5dc0917e040a3e22daae",
    "schema/m07r5-public-status.schema.json": "f49a20c0cd3fba56118f560839f45861db72e01ab38d945bac0aacc3d299c906",
}
PUBLIC_FILES = (
    STATUS,
    SCHEMA,
    ROOT / "docs/porting/m07r6-subsystem-fdc-command-gate.md",
    ROOT / ".github/workflows/m07r6-subsystem-fdc-command-gate.yml",
    ROOT / "Makefile",
)
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
    """Raised when a public M07R6 invariant fails."""


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("utf-8")


def digest(path: Path) -> str:
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
    if expected in types:
        valid = isinstance(value, types[expected])
        if expected == "integer" and isinstance(value, bool):
            valid = False
        if not valid:
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
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", len(value)):
            raise VerificationError(f"schema array length mismatch at {location}")
        if schema.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
            raise VerificationError(f"schema array duplicates at {location}")
        if isinstance(schema.get("items"), dict):
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
        raise VerificationError("public M07R6 output contains private or concrete observation material")
    if re.search(r"(?i)\b(?:physical_load_address|entry_cs_ip|load_address|first_cs_ip)\s*[:=]\s*(?:0x[0-9a-f]+|[0-9a-f]+:[0-9a-f]+|[0-9]+)", text):
        raise VerificationError("public M07R6 output contains a concrete address")
    if re.search(r"(?i)(?:^|[^a-z])/(?:users|home)/", text):
        raise VerificationError("public M07R6 output contains an absolute host path")


def validate_status(data: dict) -> None:
    expected_unresolved = sorted(FIELDS)
    if data.get("status") != "M07R6 BLOCKED — RESPONSE PRODUCER UNOBSERVABLE":
        raise VerificationError("M07R6 is not the bounded response-producer blocked result")
    if data.get("classification") != "HANDSHAKE_RESPONSE_MISSING":
        raise VerificationError("M07R6 S3 classification differs")
    boundaries = data.get("boundaries", {})
    if boundaries.get("last_reached") != "S2_MOTOR_STABLE" or boundaries.get("first_blocked") != "S3_FDC_COMMAND":
        raise VerificationError("M07R6 boundary disposition differs")
    if boundaries.get("reached") != ["S0_REQUEST_EMITTED", "S1_REQUEST_CONSUMED", "S2_MOTOR_STABLE"]:
        raise VerificationError("M07R6 reached boundaries differ")
    if boundaries.get("unreached") != ["S3_FDC_COMMAND", "S4_COMMAND_COMPLETE", "S5_SECTOR_TRANSFER", "S6_FETCH_CORRELATED", "S7_MARKER"]:
        raise VerificationError("M07R6 unreached boundaries differ")
    observations = data.get("observations", {})
    expected_observations = {
        "request_emitted": True,
        "request_consumed": True,
        "subsystem_executed": True,
        "motor_stable": True,
        "fdc_command": False,
        "command_complete": False,
        "sector_transfer": False,
        "fetch_correlated": False,
        "marker": False,
    }
    if observations != expected_observations:
        raise VerificationError("M07R6 observation record differs")
    predicate = data.get("predicate", {})
    if predicate.get("consumer_independently_observed") is not True or predicate.get("producer_fully_identified") is not False or predicate.get("scheduling_alone_used") is not False:
        raise VerificationError("M07R6 consumer/producer attribution is unsafe")
    if predicate.get("category") != "HANDSHAKE_RESPONSE_MISSING":
        raise VerificationError("M07R6 predicate category differs")
    fields = data.get("fields", {})
    if fields.get("resolved") != [] or fields.get("resolved_count") != 0 or fields.get("unresolved") != expected_unresolved:
        raise VerificationError("M07R6 mandatory fields were promoted or reordered")
    if fields.get("promotion_status") != "prohibited_pending_user_approval" or data.get("promotion_status") != fields.get("promotion_status"):
        raise VerificationError("M07R6 promotion status differs")
    trial = data.get("trial_summary", {})
    if trial.get("evidence_backed_changed_predicate_trials") != 0 or trial.get("fresh_clean_run_count") != 6 or trial.get("same_condition_pairs") != 2 or trial.get("repeated_projection_result") != "byte-identical":
        raise VerificationError("M07R6 trial summary differs")
    if data.get("validation", {}).get("s1_independently_confirmed") is not True or data["validation"].get("s0_s2_repeated") is not True:
        raise VerificationError("M07R6 repeatability gate differs")
    if data.get("private_gate", {}).get("concrete_values_published") is not False or data["private_gate"].get("input_preservation") != "passed":
        raise VerificationError("M07R6 privacy gate is unsafe")
    vaeg = data.get("vaeg", {})
    if vaeg.get("commit") != VAEG_COMMIT or vaeg.get("production_memory") is not True or vaeg.get("tests_disabled") is not True or vaeg.get("no_extra_architectural_reads") is not True:
        raise VerificationError("accepted VAEG causal-trace capability differs")


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
        raise VerificationError("M07R6 branch does not descend from accepted M07R5")
    for relative, expected in PRIOR_IDENTITIES.items():
        if digest(ROOT / relative) != expected:
            raise VerificationError(f"accepted predecessor identity changed: {relative}")
    if git("diff", "--name-only", f"{START_COMMIT}..{head}", "--", "components/").strip():
        raise VerificationError("component source or gitlink changed after M07R5")


def validate_safety() -> None:
    tracked = [item for item in git("ls-files", "-z").split("\0") if item]
    forbidden_suffixes = {".rom", ".d88", ".img", ".bin", ".exe", ".trace", ".log", ".zip", ".tar", ".gz"}
    for relative in tracked:
        if Path(relative).suffix.lower() in forbidden_suffixes:
            raise VerificationError(f"private or generated artifact is tracked: {relative}")
    for path in PUBLIC_FILES:
        if path.is_file():
            reject_public_text(path.read_text(encoding="utf-8", errors="strict"))
    if subprocess.run(["git", "check-ignore", "-q", "results/m07r6-private"], cwd=ROOT, check=False).returncode:
        raise VerificationError("M07R6 private evidence directory is not ignored")
    if "components/" in git("diff", "--cached", "--name-only"):
        raise VerificationError("component change is staged")


def verify() -> None:
    status = load_canonical(STATUS)
    schema = load_canonical(SCHEMA)
    if not isinstance(status, dict) or not isinstance(schema, dict):
        raise VerificationError("M07R6 status or schema root is not an object")
    validate_schema(status, schema)
    validate_status(status)
    validate_prior_identities()
    validate_components()
    if GOLDEN.read_text(encoding="ascii").strip() != digest(STATUS):
        raise VerificationError("M07R6 status golden is stale")
    validate_safety()
    print("M07R6 public verification passed: S0-S2 repeated, S3 response producer unresolved")


if __name__ == "__main__":
    try:
        verify()
    except (VerificationError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"M07R6 ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
