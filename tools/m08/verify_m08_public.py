#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Verify the public M08 loader and acceptance-evidence contracts."""
import hashlib
import json
from pathlib import Path
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

ROOT = Path(__file__).resolve().parents[2]
CHILD = ROOT / "components/fdkernel/pc88va"
CONTRACT_PATH = ROOT / "config/m08/loader-contract.json"
ARTIFACT_MANIFEST_PATH = ROOT / "qa/golden/m08-artifact-manifest.json"
ARTIFACT_SCHEMA_PATH = ROOT / "schema/m08-artifact-manifest.schema.json"
GOLDEN_PATH = ROOT / "qa/golden/m08-golden.json"
VAEG_QUALIFICATION_PATH = ROOT / "config/m08/vaeg-qualification.json"

PARENT_COMMIT = "3b2b203fd04765d2236594b2c39a03bf4c31a68f"
FDKERNEL_COMMIT = "105d49a72ec41afe07fc1e7b080bdbd1b3026ae2"
VAEG_COMMIT = "7463f9501d84701f50f3243d5067b6a9dfd0c2e7"
VAEG_CI = 33937050536
ARTIFACT_MANIFEST_SHA256 = "2210a590a7d705f3936a9053e197d05eb94888254b708f4435a1e7c89d3ef5e0"
ARTIFACT_SCHEMA_SHA256 = "575086b668fb7f2439f17b63a33675978fef00861eb0b30f66a7b22d3279e7fe"
VAEG_QUALIFICATION_SHA256 = "3ebbf58e18ea2acf0f92ba755cca99c3082b5ed419e6bfa51a5bd2d2fd8dbe47"
GOLDEN_SHA256 = "bd611f5d6a0cb37c16114aec5b7382cb3bf7c18d340b762501d8bc2a574ad2a7"


class VerificationError(RuntimeError):
    """Raised when public M08 evidence is missing or inconsistent."""


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"cannot read M08 JSON evidence: {path}") from exc
    if not isinstance(value, dict):
        raise VerificationError(f"M08 JSON evidence is not an object: {path}")
    return value


def _require_digest(root: Path, record: dict, key: str, expected_path: str) -> Path:
    if not isinstance(record, dict) or record.get("path") != expected_path:
        raise VerificationError(f"M08 {key} path is missing or differs")
    path = root / expected_path
    if not path.is_file() or path.is_symlink():
        raise VerificationError(f"M08 {key} is missing")
    if record.get("sha256") != _digest(path):
        raise VerificationError(f"M08 {key} digest does not match")
    return path


def validate_artifact_schema(data: dict, schema: dict) -> None:
    """Validate the schema and instance, independently of identity checks."""
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(data)
    except (SchemaError, ValidationError) as exc:
        # Do not echo instance values into diagnostics.
        raise VerificationError("M08 artifact schema conformance failed") from exc


def validate_acceptance_evidence(contract: dict, root: Path = ROOT) -> None:
    """Require every public acceptance identity before accepting M08."""
    if contract.get("status") != "accepted":
        raise VerificationError("M08 contract is not accepted")
    manifest = _require_digest(root, contract.get("public_artifact_manifest"),
                              "artifact manifest", "qa/golden/m08-artifact-manifest.json")
    golden = _require_digest(root, contract.get("public_golden"),
                             "golden", "qa/golden/m08-golden.json")
    qualification = _require_digest(root, contract.get("vaeg_qualification"),
                                    "VAEG qualification", "config/m08/vaeg-qualification.json")
    schema = root / "schema/m08-artifact-manifest.schema.json"
    if not schema.is_file() or _digest(schema) != ARTIFACT_SCHEMA_SHA256:
        raise VerificationError("M08 artifact-manifest schema is missing or differs")
    if _digest(manifest) != ARTIFACT_MANIFEST_SHA256 or _digest(golden) != GOLDEN_SHA256 or _digest(qualification) != VAEG_QUALIFICATION_SHA256:
        raise VerificationError("M08 acceptance evidence identity differs")
    data = _json(manifest)
    validate_artifact_schema(data, _json(schema))
    if data.get("schema_version") != 1 or data.get("milestone") != "M08":
        raise VerificationError("M08 artifact manifest identity differs")
    source = data.get("source", {})
    if source.get("parent_commit") != PARENT_COMMIT or source.get("fdkernel_commit") != FDKERNEL_COMMIT:
        raise VerificationError("M08 artifact source identity differs")
    if data.get("build_reproducibility") != {
        "clean_build_count": 2,
        "artifact_comparison": "byte-identical",
        "canonical_json_comparison": "byte-identical",
        "generated_outputs_not_tracked": True,
    }:
        raise VerificationError("M08 reproducibility evidence is incomplete")
    artifacts = data.get("artifacts", {})
    required_artifacts = {
        "loader_stage1": (1024, "20efd8a66dde7feac3f48df4bd6e8c4564d70e80a5a8871a8293e735c1585f24"),
        "loader_stage2": (4304, "db324cbdae11fd1e6085a7957ef171ccf9d6a9be6ea05f3df0eedf83d8f594f7"),
        "kernel_sys": (5771, "461e55d6983a944d35749eb658a5e11ba0316ff0bcd7da65982228aefce17253"),
        "raw_media": (1310720, "d19ec41d30973229df0d4e91b0344159b284f17243989a5e712eb40de5fe5724"),
        "d88_media": (1331888, "7ff2169271f4f101a8b53bb36be0343f3272d50051c2616b05d0ed4e10fa1260"),
        "extracted_kernel_sys": (5771, "461e55d6983a944d35749eb658a5e11ba0316ff0bcd7da65982228aefce17253"),
        "extracted_command_com": (91143, "fabe7744cc7c51c6f72519cc39d89bf77beaf908f994675a97a1e34c93549da1"),
        "extracted_country_sys": (42614, "04b2d2bc8df382090686f00e547d718d6706d22fb34c34dd77cd55083d5c34d5"),
    }
    if set(artifacts) != set(required_artifacts):
        raise VerificationError("M08 artifact set is incomplete")
    for name, (size, sha256) in required_artifacts.items():
        item = artifacts[name]
        if item.get("size") != size or item.get("sha256") != sha256:
            raise VerificationError(f"M08 artifact identity differs: {name}")
    if data.get("media_validation", {}).get("raw_d88_round_trip") != "byte-identical":
        raise VerificationError("M08 raw/D88 round-trip evidence is missing")
    golden_data = _json(golden)
    if golden_data.get("status") != "accepted" or golden_data.get("artifact_manifest", {}).get("sha256") != ARTIFACT_MANIFEST_SHA256:
        raise VerificationError("M08 golden does not consume the artifact manifest")
    qualification_data = _json(qualification)
    if qualification_data.get("status") != "accepted" or qualification_data.get("vaeg_commit") != VAEG_COMMIT:
        raise VerificationError("M08 VAEG qualification identity is missing")
    accepted_ci = qualification_data.get("accepted_ci", {})
    if accepted_ci.get("run_id") != VAEG_CI or accepted_ci.get("conclusion") != "success":
        raise VerificationError("M08 VAEG CI evidence is incomplete")
    if qualification_data.get("qualification", {}).get("fresh_clean_runs") != 2 or qualification_data.get("qualification", {}).get("canonical_projection") != "byte-identical":
        raise VerificationError("M08 private two-run qualification is incomplete")
    if contract.get("vaeg_qualification", {}).get("commit") != VAEG_COMMIT or contract.get("vaeg_qualification", {}).get("accepted_ci_run") != VAEG_CI:
        raise VerificationError("M08 contract does not pin the qualified VAEG identity")


def main():
    contract = _json(CONTRACT_PATH)
    if contract["platform"] != "pc88va" or contract["replace_stubs"] != ["pc88va_disk_read", "pc88va_loader_handoff"]:
        raise SystemExit("M08 public loader contract differs")
    if contract["promotion_status"] != "prohibited_pending_user_approval" or contract["hardware_claim"] or contract["dos_runtime_claim"]:
        raise SystemExit("M08 public boundary claims are unsafe")
    required = [CHILD / "boot" / name for name in ("disk_read.inc", "fat12.inc", "root_directory.inc", "file_load.inc", "mz_validate.inc", "mz_transform.inc", "loader_handoff.inc", "stage1.asm", "stage2.asm")]
    if any(not p.is_file() for p in required):
        raise SystemExit("M08 loader source boundary is incomplete")
    try:
        validate_acceptance_evidence(contract)
    except VerificationError as exc:
        raise SystemExit(str(exc))
    print("M08 public parameterized loader and acceptance evidence PASS")


if __name__ == "__main__":
    main()
