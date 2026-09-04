#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Verify the privacy-safe public M07 completion contract."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATUS = ROOT / "config/m07/m07-completion-public-status.json"
SCHEMA = ROOT / "schema/m07-completion-public-status.schema.json"
GOLDEN = ROOT / "qa/golden/m07-completion-public-status.sha256"
START_COMMIT = "98ac0c8d0ab9720c35d76ccfb57c6aa23d4933a2"
VAEG_START = "e1fddddc98c6534a1dc1d4938bd6fad2b246ebb3"
VAEG_FINAL = "d68b1ab7392cedc7080927c24a8aa4b35c6756cb"
VAEG_CI = 33887608335
VAEG_P1 = "0f326a8d0bc84c674d08e3dff475fed5477c626855e8821b4a89af17451aa707"
SYNTHETIC_TRACE = "6a253f9f0b25e74cf0c95f27d378586c141f821b2f77c8704f3237436f515d9b"
COMPONENTS = {
    "components/fdkernel": "69ccdd8699895722fc537d647ec490685532bdc4",
    "components/freecom": "855281a3114b43ad4b8d9a320f2aca39be046bba",
    "components/country": "23f189cca3420606eae8723884fa92ccd65eb307",
}
PRIOR_IDENTITIES = {
    "tools/m07/probe.asm": "ae17a5dcd461e80b2a0ca6db73333eebb461d81a0bb9589e464731c4f5bdfa7b",
    "config/m07/variants.json": "fdc75b8353c2d1c8a858a86cbabd47eecd6327133c47184c8606f00c4a62768e",
    "schema/m07-public-result.schema.json": "4a314a29b243660d9fe796811cfe62f8799646551c4c53a08b410cb01c9fdc73",
    "schema/m07-private-overlay.schema.json": "e4b6e3eb67280e197c89f142e4e4d29ddc1705476eaebc868839e79de4c7e2a4",
    "qa/golden/m07-probe-manifest.json": "fb7637082efeb2d4f57437d723d22453b6493904b7d3e805230e6d00d93aeadd",
    "config/m07/m07r6-public-status.json": "590519252c1b49b34c3160b1855c639b3bebbc36c1b2158a1d49f2115cf2fa59",
    "schema/m07r6-public-status.schema.json": "00ae797fb7a9e40e014d3c4848362163357be9b3f2be64032bdedee8936c9ab8",
}
G_BOUNDARIES = [
    "G0_REQUEST_ACCEPTED",
    "G1_ROUTE_SELECTED",
    "G2_MAILBOX_ENQUEUE_ATTEMPTED",
    "G3_MAILBOX_ENQUEUE_COMMITTED",
    "G4_MAILBOX_REQUEST_VISIBLE",
    "G5_SUBSYSTEM_DISPATCHED",
    "G6_MAILBOX_DEQUEUE_ATTEMPTED",
    "G7_CONSUMER_CALLBACK_ENTERED",
    "G8_REQUEST_CONSUMED",
    "G9_RESPONSE_ELIGIBLE",
]
H_BOUNDARIES = [
    "H0_RESPONSE_PRODUCED",
    "H1_RESPONSE_DELIVERED",
    "H2_FDC_COMMAND_ATTEMPTED",
    "H3_FDC_COMMAND_ISSUED",
    "H4_SECTOR_REQUESTED",
    "H5_SECTOR_FOUND",
    "H6_DMA_OR_TRANSFER_STARTED",
    "H7_SECTOR_DATA_COMMITTED",
    "H8_FDC_COMPLETION_REPORTED",
    "H9_FIRMWARE_ACCEPTED_RECORD",
]
FIELDS = [
    "accepted_signature_profile",
    "boot_drive_identity",
    "first_cs_ip",
    "firmware_attempts_m05_geometry",
    "initial_register_state",
    "initial_sector_reads",
    "loaded_extent",
    "physical_load_address",
]
PUBLIC_FILES = (
    STATUS,
    SCHEMA,
    ROOT / "docs/porting/m07-report.md",
    ROOT / ".github/workflows/m07-completion.yml",
    ROOT / "Makefile",
)
FORBIDDEN = (
    "pc88va-private-docs",
    "rom_basename",
    "rom_sha256",
    "trace_excerpt",
    "sector_dump",
    "private_overlay_value",
    "winning_variant",
    "concrete_address",
)


class VerificationError(RuntimeError):
    """Raised when the public M07 completion record is unsafe or inconsistent."""


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
    types = {"null": type(None), "object": dict, "array": list, "string": str,
             "integer": int, "boolean": bool}
    expected = schema.get("type")
    if expected is not None:
        names = expected if isinstance(expected, list) else [expected]
        valid = any(isinstance(value, types[name]) for name in names)
        if "integer" in names and isinstance(value, bool):
            valid = False
        if not valid:
            raise VerificationError(f"schema type mismatch at {location}")
    if "const" in schema and value != schema["const"]:
        raise VerificationError(f"schema constant mismatch at {location}")
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


def validate_status(data: dict) -> None:
    if data.get("status") != "M07 PASS — VAEG FIRMWARE BOOT ACCEPTANCE CONTRACT COMPLETE":
        raise VerificationError("M07 completion status differs")
    if data.get("milestone") != "M07" or data.get("version") != 1:
        raise VerificationError("M07 completion identity differs")
    if data.get("classification") != "VAEG_FIRMWARE_BOOT_ACCEPTANCE_CONTRACT_COMPLETE":
        raise VerificationError("M07 completion classification differs")
    boundaries = data.get("boundaries", {})
    if boundaries.get("g_reached") != G_BOUNDARIES or boundaries.get("h_reached") != H_BOUNDARIES:
        raise VerificationError("M07 correlated boundary sequence differs")
    if boundaries.get("first_absent") is not None or boundaries.get("last_reached") != H_BOUNDARIES[-1]:
        raise VerificationError("M07 final boundary disposition differs")
    if not all(data.get("observations", {}).values()):
        raise VerificationError("M07 public observations are incomplete")
    fields = data.get("fields", {})
    items = fields.get("items", [])
    if [item.get("id") for item in items] != FIELDS:
        raise VerificationError("M08 handoff field names or ordering differ")
    if fields.get("resolved_count") != 8 or fields.get("unresolved") != []:
        raise VerificationError("M08 handoff fields are not 8/8 resolved")
    if any(item.get("publication_state") != "resolved_private" for item in items):
        raise VerificationError("a private M08 field was promoted or left unresolved")
    if any(item.get("evidence_class") not in {"DYNAMICALLY_OBSERVED", "CROSS_VALIDATED"} for item in items):
        raise VerificationError("an M08 field lacks accepted evidence classification")
    private_gate = data.get("private_gate", {})
    expected_private = {
        "accepted_clean_run_count": 18,
        "accepted_pair_count": 9,
        "concrete_values_published": False,
        "input_preservation": "passed",
        "performed": True,
        "persistent_evidence_retained": True,
        "projection_determinism": "byte-identical",
        "result": "conclusive",
    }
    if private_gate != expected_private:
        raise VerificationError("M07 private-gate abstract record differs")
    if data.get("promotion_status") != "prohibited_pending_user_approval":
        raise VerificationError("M07 private facts were promoted without approval")
    validation = data.get("validation", {})
    if validation != {"hardware": "not_run", "m08": "not_started",
                       "private_leakage": "absent", "public_probe_changed": False}:
        raise VerificationError("M07 validation boundary differs")
    historical = data.get("historical", {})
    if historical.get("m07r6_status_preserved") is not True:
        raise VerificationError("M07R6 historical status was not preserved")
    if historical.get("m07r6_status_sha256") != PRIOR_IDENTITIES["config/m07/m07r6-public-status.json"]:
        raise VerificationError("M07R6 status identity differs")
    if historical.get("root_cause_categories") != [
        "READ_ONLY_D88_OPEN_MODE",
        "SUBSYSTEM_REQUEST_LATCH_PORT_MAPPING",
        "TRACE_REQUEST_CORRELATION",
    ]:
        raise VerificationError("M07 root-cause categories differ")
    vaeg = data.get("vaeg", {})
    expected_vaeg = {
        "accepted_ci_conclusion": "success",
        "accepted_ci_run_id": VAEG_CI,
        "final_commit": VAEG_FINAL,
        "flat_test_memory_absent": True,
        "no_extra_architectural_reads": True,
        "p1_binary_sha256": VAEG_P1,
        "production_memory": True,
        "repository": "https://github.com/nakatamaho/vaeg.git",
        "start_commit": VAEG_START,
        "synthetic_trace_sha256": SYNTHETIC_TRACE,
        "tests_disabled_p1": True,
        "two_clean_p1_builds": "byte-identical",
    }
    if vaeg != expected_vaeg:
        raise VerificationError("accepted VAEG completion evidence differs")
    if data.get("components") != {"clean": True, "gitlinks": COMPONENTS}:
        raise VerificationError("component public status differs")


def validate_components() -> None:
    for relative, expected in COMPONENTS.items():
        stage = git("ls-files", "--stage", "--", relative).split()
        if len(stage) < 2 or stage[0] != "160000" or stage[1] != expected:
            raise VerificationError(f"component gitlink drift: {relative}")
        if git("rev-parse", "HEAD", cwd=ROOT / relative).strip() != expected:
            raise VerificationError(f"component checkout drift: {relative}")
        if git("status", "--short", "--untracked-files=all", cwd=ROOT / relative):
            raise VerificationError(f"component worktree is dirty: {relative}")


def validate_history() -> None:
    head = git("rev-parse", "HEAD").strip()
    if subprocess.run(["git", "merge-base", "--is-ancestor", START_COMMIT, head],
                      cwd=ROOT, check=False).returncode:
        raise VerificationError("M07 completion branch does not descend from M07R6")
    for relative, expected in PRIOR_IDENTITIES.items():
        if digest(ROOT / relative) != expected:
            raise VerificationError(f"accepted M07 identity changed: {relative}")
    if git("diff", "--name-only", f"{START_COMMIT}..{head}", "--", "components/").strip():
        raise VerificationError("component source or gitlink changed after M07R6")


def reject_public_text(text: str) -> None:
    lowered = text.lower()
    if any(marker in lowered for marker in FORBIDDEN):
        raise VerificationError("public M07 completion output contains private material")
    if re.search(r"(?i)(?:^|[^a-z])/(?:users|home|private/tmp)/", text):
        raise VerificationError("public M07 completion output contains a host path")
    if re.search(r"(?i)\b(?:physical_load_address|first_cs_ip|loaded_extent)\s*[:=]\s*(?:0x[0-9a-f]+|[0-9a-f]+:[0-9a-f]+|[0-9]+)", text):
        raise VerificationError("public M07 completion output contains a concrete handoff value")


def validate_safety() -> None:
    tracked = [item for item in git("ls-files", "-z").split("\0") if item]
    forbidden_suffixes = {".rom", ".d88", ".img", ".bin", ".exe", ".trace", ".log", ".zip"}
    for relative in tracked:
        if Path(relative).suffix.lower() in forbidden_suffixes:
            raise VerificationError(f"private or generated artifact is tracked: {relative}")
    for path in PUBLIC_FILES:
        reject_public_text(path.read_text(encoding="utf-8", errors="strict"))
    if subprocess.run(["git", "check-ignore", "-q", "results/m07-private"],
                      cwd=ROOT, check=False).returncode:
        raise VerificationError("private M07 result namespace is not ignored")
    if "components/" in git("diff", "--cached", "--name-only"):
        raise VerificationError("component change is staged")


def verify() -> None:
    status = load_canonical(STATUS)
    schema = load_canonical(SCHEMA)
    if not isinstance(status, dict) or not isinstance(schema, dict):
        raise VerificationError("M07 status or schema root is not an object")
    validate_schema(status, schema)
    validate_status(status)
    validate_history()
    validate_components()
    if GOLDEN.read_text(encoding="ascii").strip() != digest(STATUS):
        raise VerificationError("M07 completion status golden is stale")
    validate_safety()
    print("M07 completion public verification passed: G0-G9, H0-H9, and 8/8 private fields recorded")


if __name__ == "__main__":
    try:
        verify()
    except (VerificationError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"M07 COMPLETION ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
