#!/usr/bin/env python3
"""Validate the provisional M04 boot/media contract and local text evidence."""

import argparse
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "qa"))
from current_components import CurrentComponentError, resolve_current_components


ACCEPTED_PARENT = "5bb5e1f47b0fdb954056532412889cee1123ef1b"
COMPONENTS = {
    "country": "23f189cca3420606eae8723884fa92ccd65eb307",
    "fdkernel": "6523acdb87f4665e6068ea331859885267242005",
    "freecom": "855281a3114b43ad4b8d9a320f2aca39be046bba",
}
IDENTITIES = {
    "components_lock": ("manifests/components.lock.json", "440e481b28c740875489a6953a246ce5370c44074053c7aad3f80e79ec40c19c"),
    "toolchain_lock": ("manifests/toolchains.lock.json", "39c5b3052d71463235a26e8704ab54c1fedb51ee75bb4efb55e6229391a95162"),
    "m01_contract": ("manifests/m01-build-contract.json", "7d66be32b508395d8c36a902389f368e9f38d9abab08085bda89e3d2c5d6d578"),
    "m01_golden": ("qa/golden/m01-baseline.json", "6fcfe834f90ffc602589ddc63b50d90eba33bbc1802b6bff3c9ef6b9d397c7c3"),
    "m02_golden": ("qa/golden/m02/bundle-manifest.json", "4d4e92f92911130109b5b140b2202fc1dfc3abb9af3cd7501b685894d0cb78fd"),
    "m03r1_golden": ("qa/golden/m03/port-surface.json", "d871c7f188313218c2c9481ea9fe7c6abf6acd6369f996b2641021ad27c80550"),
    "m03r1_routing": ("config/m03/milestone-routing.json", "dbb28f45c16d59b97fab8defa21ce4a866d51c701826987ce26a3b50ad8c938e"),
    "m03r1_schema": ("config/m03/census-schema.json", "08af162ec4c6def748ebc57e1b48aa7e38a82e203615feb736458b53c8b35548"),
    "m03r1_projection": ("qa/golden/m03/observation-projection.json", "1db787d815f7af6a9748e3f691e5ad7669f452921c8d65178ce692fb4a6640cc"),
}
M02_KERNEL_SIZE = 83774
M02_KERNEL_SHA256 = "3ebddb01abe5e39f16d27439836be283c57d454f012d3c990f01fa8a2b14101d"
CONSUMED_IDENTITIES = {
    "components_lock_sha256": "440e481b28c740875489a6953a246ce5370c44074053c7aad3f80e79ec40c19c",
    "m01_contract_sha256": "7d66be32b508395d8c36a902389f368e9f38d9abab08085bda89e3d2c5d6d578",
    "m01_golden_sha256": "6fcfe834f90ffc602589ddc63b50d90eba33bbc1802b6bff3c9ef6b9d397c7c3",
    "m02_golden_sha256": "4d4e92f92911130109b5b140b2202fc1dfc3abb9af3cd7501b685894d0cb78fd",
    "m02_sidecar_sha256": "0ffe8a10fd1c430fc876a7387e44fe6084be5b21deaf93bb8826a3b13b278fbb",
    "m02_tar_sha256": "00fb02b03ea16423b5987d455a8ea11a8a567c699484656228722119c6239e51",
    "m02_tar_size": 399360,
    "m03r1_census_entries": 14455,
    "m03r1_golden_sha256": "d871c7f188313218c2c9481ea9fe7c6abf6acd6369f996b2641021ad27c80550",
    "m03r1_projection_sha256": "70bee9fedaa526f58a795c2acd43e3492a23e1554bcf843160bce7316120a42c",
    "m03r1_projection_size": 10039882,
    "m03r1_routing_sha256": "dbb28f45c16d59b97fab8defa21ce4a866d51c701826987ce26a3b50ad8c938e",
    "m03r1_ruleset_sha256": "57b8b299537bb9ca226e48cbd5bbf5dfe19da87d89ca3250c56a008fb9b0934c",
    "m03r1_schema_sha256": "08af162ec4c6def748ebc57e1b48aa7e38a82e203615feb736458b53c8b35548",
    "toolchain_lock_sha256": "39c5b3052d71463235a26e8704ab54c1fedb51ee75bb4efb55e6229391a95162",
}
CONTRACT_RELATIVE = "config/contracts/m04-provisional-pc88va-boot-media.json"
SCHEMA_RELATIVE = "config/contracts/m04-provisional-pc88va-boot-media.schema.json"
EVIDENCE_RELATIVE = "config/contracts/m04-evidence-matrix.json"
SOURCE_REGISTER_RELATIVE = "docs/references/pc88va-source-register.md"
GOLDEN_RELATIVE = "qa/golden/m04/contract.sha256"
REQUIRED_QUESTIONS = {
    "M04-BOOT-ENTRY-STATE",
    "M04-BOOT-INTERRUPTS",
    "M04-BOOT-IPL-LOAD",
    "M04-BOOT-SECTOR-FORMAT",
    "M04-BOOT-TIMER",
    "M04-BPB-MEDIA",
    "M04-DISK-SERVICE",
    "M04-EARLY-CONSOLE",
    "M04-FDC-DMA-IRQ",
    "M04-FLOPPY-GEOMETRY",
    "M04-KEYBOARD-ENCODING",
    "M04-KERNEL-LOAD",
}
FIELD_KEYS = {"claim_ids", "confidence", "status", "validation_target", "value"}
STATUSES = {
    "confirmed", "supported", "working_assumption", "design_choice",
    "private_observation", "unknown_reported", "deferred", "conflict",
}
CONFIDENCES = {"high", "medium", "low", "none"}
READINESS = {"ready", "ready_with_assumptions", "blocked", "not_applicable"}
CLAIM_TYPES = {
    "electronic_document_fact", "text_export_fact", "source_fact",
    "rom_observation", "d88_observation", "private_binary_correlation",
    "derived_value", "design_choice", "working_assumption",
    "unknown_reported", "deferred", "conflict",
}
PRIVATE_MARKERS = (
    "pc88va-private-docs", "m04-private-overlay", "m04-private/",
    "varom00_mame_baddump.rom", ".d88", ".rom",
)
UNSTABLE_KEYS = {"timestamp", "generated_at", "created_at", "hostname", "username", "cwd", "absolute_path"}


class VerificationError(Exception):
    """A bounded fail-closed M04 validation error."""


def canonical_json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes())


def load_canonical(path):
    path = Path(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"cannot parse JSON {path}: {exc}") from exc
    if path.read_bytes() != canonical_json_bytes(value):
        raise VerificationError(f"JSON is not canonical: {path}")
    return value


def git(root, *args, check=True):
    result = subprocess.run(["git", *args], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if check and result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip().replace("\n", " | ")
        raise VerificationError(f"git {' '.join(args)} failed: {detail}")
    return result


def git_text(root, *args):
    return git(root, *args).stdout.decode("utf-8", errors="strict").strip()


def reject_unstable(value, label="contract"):
    if isinstance(value, float):
        raise VerificationError(f"floating point is not canonical: {label}")
    if isinstance(value, dict):
        for key, item in value.items():
            if key in UNSTABLE_KEYS:
                raise VerificationError(f"unstable field is prohibited: {label}.{key}")
            reject_unstable(item, f"{label}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            reject_unstable(item, f"{label}[{index}]")
    elif isinstance(value, str):
        if value.startswith(("/", "file://")) or re.match(r"^[A-Za-z]:[\\/]", value):
            raise VerificationError(f"absolute path is prohibited: {label}")
        if re.match(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}", value):
            raise VerificationError(f"wall-clock timestamp is prohibited: {label}")


def reject_private_text(text, label="tracked M04 evidence"):
    lower = text.lower()
    if text.startswith(("/", "file://")) or re.search(r"(?:^|[\s`'\"])[A-Za-z]:[\\/]", text):
        raise VerificationError(f"absolute path is prohibited in {label}")
    for marker in PRIVATE_MARKERS:
        if marker.lower() in lower:
            raise VerificationError(f"private binary/path marker is prohibited in {label}: {marker}")
    if re.search(r"\b(?:sector dump|rom string|disassembly dump|private hash)\b", lower):
        raise VerificationError(f"private analysis content is prohibited in {label}")


def validate_model_observations(records):
    for record in records:
        models = record.get("models", [])
        if len(set(models)) > 1:
            raise VerificationError("VA and VA2 private observations must remain model-separated")


def validate_boot_candidate_support(record):
    if record.get("assumes_first_physical_sector") and not record.get("txt_or_rom_claim_ids"):
        raise VerificationError("D88 first-sector boot assumption lacks TXT or firmware support")


def verify_input_preservation(before, after):
    if sha256_bytes(before) != sha256_bytes(after):
        raise VerificationError("private binary input changed during analysis")


def validate_integer_hex(integer, rendering):
    if not isinstance(integer, int) or not isinstance(rendering, str) or int(rendering, 16) != integer:
        raise VerificationError("integer and hexadecimal rendering disagree")


def validate_pc88va_source(material):
    if material in {"nec98", "pc98"}:
        raise VerificationError("PC-98 or NEC98 evidence cannot establish a PC-88VA hardware fact")


def validate_ci_boundary(statement):
    lower = statement.lower()
    if "ci" in lower and "private" in lower and any(word in lower for word in ("inspected", "verified", "validated contents")):
        raise VerificationError("CI cannot claim it inspected private source contents")


def parse_synthetic_d88(data):
    """Parse a minimal D88 byte string for newly authored unit fixtures only."""
    if len(data) < 0x2B0:
        raise VerificationError("synthetic D88 header is truncated")
    declared = struct.unpack_from("<I", data, 0x1C)[0]
    if declared < 0x2B0 or declared > len(data):
        raise VerificationError("synthetic D88 declared size is out of bounds")
    offsets = [item for item in struct.unpack_from("<164I", data, 0x20) if item]
    if offsets != sorted(set(offsets)) or any(item < 0x2B0 or item >= declared for item in offsets):
        raise VerificationError("synthetic D88 track offsets are invalid")
    sectors = []
    for index, start in enumerate(offsets):
        end = offsets[index + 1] if index + 1 < len(offsets) else declared
        cursor = start
        expected = None
        while cursor < end:
            if cursor + 16 > end:
                raise VerificationError("synthetic D88 sector header is out of bounds")
            count = struct.unpack_from("<H", data, cursor + 4)[0]
            length = struct.unpack_from("<H", data, cursor + 14)[0]
            if not count or not length or cursor + 16 + length > end:
                raise VerificationError("synthetic D88 sector payload is out of bounds")
            expected = count if expected is None else expected
            if count != expected:
                raise VerificationError("synthetic D88 track sector counts disagree")
            sectors.append(tuple(data[cursor:cursor + 4]) + (length,))
            cursor += 16 + length
        if cursor != end or expected is None:
            raise VerificationError("synthetic D88 track extent is invalid")
    return sectors


def validate_changed_paths(paths):
    allowed = (
        ".github/workflows/m04-boot-media-contract.yml", ".gitignore", "Makefile",
        "config/contracts/m04-", "docs/adr/0002-", "docs/contracts/m04-",
        "docs/porting/m04-", "docs/references/pc88va-source-register.md",
        "qa/golden/m04/", "tests/m04/", "tools/m03/verify_m03.py", "tools/m04/",
    )
    m04r1_license_paths = {
        ".github/workflows/m04r1-license.yml",
        "COPYING",
        "LICENSE.md",
        "docs/licensing/README.md",
        "manifests/licenses.yml",
        "tests/qa/test_verify_license_policy.py",
        "tools/qa/verify_license_policy.py",
    }
    m05_paths = {
        ".github/workflows/m05-media.yml",
        "docs/porting/m05-media-image.md",
        "qa/golden/m05-media-manifest.json",
    }
    m05_prefixes = ("config/m05/", "tests/m05/", "tools/m05/")
    m06_paths = {
        ".github/workflows/m06-kernel.yml", ".gitignore", "Makefile",
        "components/fdkernel", "manifests/README.md",
        "manifests/m06-components.lock.json", "qa/golden/m06-kernel-manifest.json",
        "schema/m06-kernel-interface.schema.json", "tools/verify_scaffold.py",
        "tools/m01/build_baseline.sh", "tools/m01/verify_m01.py",
        "tools/m02/common.py", "tools/m04/verify_m04.py", "tools/m05/common.py",
        "tools/m05/verify_m05.py", "tools/qa/current_components.py",
        "tools/qa/verify_license_policy.py",
    }
    m06_prefixes = ("config/m06/", "docs/porting/m06-", "tests/m06/", "tools/m06/")
    protected = (
        "components/", "manifests/", "qa/golden/m01", "qa/golden/m02",
        "qa/golden/m03", "config/m03/", "tools/m01/", "tools/m02/", "tools/m03/",
        "qa/results/", "pc88va/", "necpc88va/",
    )
    binary_suffixes = {".rom", ".d88", ".bin", ".obj", ".o", ".img", ".ima", ".tar", ".zip", ".log"}
    for item in paths:
        path = PurePosixPath(item)
        if item in m04r1_license_paths:
            continue
        if item in m05_paths or item.startswith(m05_prefixes):
            continue
        if item in m06_paths or item.startswith(m06_prefixes):
            continue
        if item == "tools/m03/verify_m03.py":
            continue
        if any(item.startswith(prefix) for prefix in protected) or path.suffix.lower() in binary_suffixes:
            raise VerificationError(f"M04 changed a protected or generated path: {item}")
        if not any(item == prefix or item.startswith(prefix) for prefix in allowed):
            raise VerificationError(f"path is outside M04 parent-only scope: {item}")


def verify_baseline(root):
    root = Path(root).resolve()
    if root.name != "freedos-pc88va" or Path(git_text(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise VerificationError("repository root identity mismatch")
    head = git_text(root, "rev-parse", "HEAD")
    if git(root, "merge-base", "--is-ancestor", ACCEPTED_PARENT, head, check=False).returncode:
        raise VerificationError("accepted M03R1 commit is not an ancestor of HEAD")
    for _, (relative, expected) in IDENTITIES.items():
        if sha256_file(root / relative) != expected:
            raise VerificationError(f"accepted identity mismatch: {relative}")
    historical = {f"components/{name}": commit for name, commit in COMPONENTS.items()}
    try:
        current = resolve_current_components(root, historical)
    except CurrentComponentError as exc:
        raise VerificationError(str(exc)) from exc
    for relative, expected in current.items():
        name = PurePosixPath(relative).name
        if git_text(root, "rev-parse", f":{relative}") != expected:
            raise VerificationError(f"component gitlink mismatch: {name}")
        component = root / relative
        if git_text(component, "rev-parse", "HEAD") != expected:
            raise VerificationError(f"component checkout mismatch: {name}")
        if git_text(component, "status", "--short", "--untracked-files=all"):
            raise VerificationError(f"component worktree is dirty: {name}")
    return head


def validate_evidence(data):
    if data.get("schema_version") != 1 or not isinstance(data.get("claims"), list):
        raise VerificationError("evidence matrix schema is invalid")
    ids = set()
    for claim in data["claims"]:
        claim_id = claim.get("claim_id")
        if not isinstance(claim_id, str) or claim_id in ids:
            raise VerificationError("evidence claim ID is missing or duplicated")
        ids.add(claim_id)
        if claim.get("claim_type") not in CLAIM_TYPES or claim.get("status") not in STATUSES or claim.get("confidence") not in CONFIDENCES:
            raise VerificationError(f"invalid evidence vocabulary: {claim_id}")
        if claim["claim_type"] in {"electronic_document_fact", "text_export_fact"}:
            if not all(claim.get(key) for key in ("source_id", "basename", "encoding", "section")):
                raise VerificationError(f"document claim lacks a locator: {claim_id}")
            if not isinstance(claim.get("line_start"), int) or not isinstance(claim.get("line_end"), int) or not 0 < claim["line_start"] <= claim["line_end"]:
                raise VerificationError(f"document claim line range is invalid: {claim_id}")
        if claim["claim_type"] == "text_export_fact" and claim["status"] == "confirmed":
            raise VerificationError(f"uncorroborated text export cannot be confirmed: {claim_id}")
        if claim["claim_type"] in {"working_assumption", "unknown_reported", "deferred"} and not claim.get("downstream_validation"):
            raise VerificationError(f"claim lacks downstream routing: {claim_id}")
    return ids


def iter_field_records(value, path="contract"):
    if isinstance(value, dict):
        if FIELD_KEYS.issubset(value):
            yield path, value
        else:
            for key, item in value.items():
                yield from iter_field_records(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from iter_field_records(item, f"{path}[{index}]")


def validate_field_records(data, claim_ids):
    count = 0
    for path, record in iter_field_records(data):
        count += 1
        if record["status"] not in STATUSES or record["confidence"] not in CONFIDENCES:
            raise VerificationError(f"invalid field status/confidence: {path}")
        if not isinstance(record["claim_ids"], list) or record["claim_ids"] != sorted(set(record["claim_ids"])):
            raise VerificationError(f"field claim IDs are not unique and sorted: {path}")
        if record["value"] is not None and not record["claim_ids"]:
            raise VerificationError(f"non-null field has no claim: {path}")
        if any(item not in claim_ids for item in record["claim_ids"]):
            raise VerificationError(f"field references an unknown claim: {path}")
        if record["status"] == "working_assumption" and not record["validation_target"]:
            raise VerificationError(f"working assumption has no validation target: {path}")
        control_record = ".readiness." in path or path.endswith(".disposition")
        if record["status"] == "private_observation" or (
            record["status"] in {"unknown_reported", "conflict"} and not control_record
        ):
            if record["value"] is not None:
                raise VerificationError(f"redacted or unresolved field exposes a value: {path}")
            if not record["validation_target"]:
                raise VerificationError(f"unresolved field has no downstream impact: {path}")
    if count < 30:
        raise VerificationError("contract contains too few auditable field records")


def get_value(section, key):
    record = section[key]
    if not isinstance(record, dict) or not FIELD_KEYS.issubset(record):
        raise VerificationError(f"contract field is not auditable: {key}")
    return record["value"]


def validate_arithmetic(data):
    medium = data["selected_candidate_medium"]
    bps = get_value(medium, "bytes_per_sector")
    spt = get_value(medium, "sectors_per_track")
    heads = get_value(medium, "heads")
    cylinders = get_value(medium, "cylinders")
    total = get_value(medium, "total_sectors")
    image_bytes = get_value(medium, "total_bytes")
    if total != cylinders * heads * spt or image_bytes != total * bps:
        raise VerificationError("candidate medium capacity arithmetic mismatch")
    fs = data["filesystem"]
    reserved = get_value(fs, "reserved_sectors")
    fats = get_value(fs, "fat_count")
    spf = get_value(fs, "sectors_per_fat")
    roots = get_value(fs, "root_entries")
    spc = get_value(fs, "sectors_per_cluster")
    root_sectors = (roots * 32 + bps - 1) // bps
    first_data = reserved + fats * spf + root_sectors
    data_sectors = total - first_data
    clusters = data_sectors // spc
    fat_bytes_needed = ((clusters + 2) * 3 + 1) // 2
    if get_value(fs, "root_directory_sectors") != root_sectors or get_value(fs, "first_data_sector") != first_data:
        raise VerificationError("FAT/root/data boundary mismatch")
    if get_value(fs, "data_sectors") != data_sectors or get_value(fs, "data_clusters") != clusters:
        raise VerificationError("derived FAT12 data region mismatch")
    if not 1 <= clusters < 4085 or spf * bps < fat_bytes_needed:
        raise VerificationError("candidate FAT is not a sufficient FAT12 layout")
    if get_value(fs, "fat_bytes_required") != fat_bytes_needed:
        raise VerificationError("FAT byte requirement mismatch")
    addressing = data["addressing"]
    sector_base = get_value(addressing, "physical_sector_id_base")
    if sector_base != get_value(medium, "physical_sector_id_base") or sector_base != 1:
        raise VerificationError("physical sector-ID base is inconsistent")
    for lba in (0, spt - 1, spt, total - 1):
        cylinder = lba // (heads * spt)
        remainder = lba % (heads * spt)
        head = remainder // spt
        sector = remainder % spt + sector_base
        round_trip = (cylinder * heads + head) * spt + sector - sector_base
        if round_trip != lba:
            raise VerificationError("CHS/LBA round trip mismatch")
    kernel = data["kernel_payload_role"]
    if get_value(kernel, "accepted_baseline_size") != M02_KERNEL_SIZE or get_value(kernel, "accepted_baseline_sha256") != M02_KERNEL_SHA256:
        raise VerificationError("accepted kernel payload identity mismatch")
    if M02_KERNEL_SIZE > data_sectors * bps:
        raise VerificationError("accepted kernel payload does not fit candidate medium")
    if get_value(kernel, "on_disk_name") != "KERNEL.SYS":
        raise VerificationError("kernel payload name is not the selected 8.3 name")


def validate_readiness(data):
    readiness = data.get("readiness")
    if not isinstance(readiness, dict) or set(readiness) != {"private_local", "public"}:
        raise VerificationError("readiness matrix is incomplete")
    for audience, entries in readiness.items():
        if set(entries) != {"M05", "M06", "M07", "M08"}:
            raise VerificationError(f"{audience} readiness does not cover M05-M08")
        for milestone, record in entries.items():
            if get_value(entries, milestone) not in READINESS:
                raise VerificationError(f"invalid readiness state: {audience}.{milestone}")
    for milestone in ("M05", "M06"):
        if get_value(readiness["public"], milestone) not in {"ready", "ready_with_assumptions"}:
            raise VerificationError(f"M04 cannot pass because {milestone} is not ready")
    evaluated = {item["name"]: item["status"] for item in data.get("derived_invariants", [])}
    for name in ("media_capacity", "fat12_capacity", "chs_lba_round_trip", "kernel_payload_fit"):
        if evaluated.get(name) != "evaluated_pass":
            raise VerificationError(f"M05-required invariant is not evaluable: {name}")


def validate_schema_shape(schema):
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise VerificationError("M04 schema draft identity is invalid")
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        raise VerificationError("M04 schema does not fail closed at the top level")
    if "field" not in schema.get("$defs", {}):
        raise VerificationError("M04 schema lacks the auditable field definition")


def validate_contract_data(data, claim_ids):
    required = {
        "addressing", "blocker_dispositions", "boot_record", "candidate_media",
        "component_gitlinks", "consumed_identities", "contract_id", "contract_status",
        "derived_invariants", "disk_access_candidates", "early_diagnostics",
        "evidence_matrix_digest", "filesystem", "firmware_dependency",
        "firmware_to_ipl", "kernel_loading", "kernel_payload_role", "open_questions",
        "parent_commit", "preferred_disk_access", "readiness", "schema_version",
        "selected_candidate_medium", "source_registry_digest", "target_model",
    }
    if set(data) != required or data["schema_version"] != 1 or data["contract_status"] != "provisional":
        raise VerificationError("contract top-level schema is invalid")
    if data["parent_commit"] != ACCEPTED_PARENT or data["component_gitlinks"] != COMPONENTS:
        raise VerificationError("contract baseline identity mismatch")
    if data["consumed_identities"] != CONSUMED_IDENTITIES:
        raise VerificationError("contract consumed-identity set mismatch")
    if {item.get("question_id") for item in data["blocker_dispositions"]} != REQUIRED_QUESTIONS:
        raise VerificationError("the twelve M03 blockers are not fully classified")
    validate_field_records(data, claim_ids)
    validate_arithmetic(data)
    validate_readiness(data)
    reject_unstable(data)
    reject_private_text(json.dumps(data, ensure_ascii=False), "public contract")


def validate_sidecar(root):
    contract = root / CONTRACT_RELATIVE
    expected = f"{sha256_file(contract)}  {contract.name}\n"
    try:
        actual = (root / GOLDEN_RELATIVE).read_text(encoding="ascii")
    except (OSError, UnicodeError) as exc:
        raise VerificationError(f"cannot read M04 golden sidecar: {exc}") from exc
    if actual != expected:
        raise VerificationError("M04 contract sidecar mismatch")


def validate_public_files(root):
    paths = [
        CONTRACT_RELATIVE, SCHEMA_RELATIVE, EVIDENCE_RELATIVE,
        SOURCE_REGISTER_RELATIVE,
        "docs/contracts/m04-provisional-pc88va-boot-media.md",
        "docs/porting/m04-evidence-matrix.md",
        "docs/porting/m04-blocker-dispositions.md",
        "docs/porting/m04-readiness.md",
        "docs/porting/m04-open-questions.md",
        "docs/adr/0002-pc88va-candidate-boot-path-and-medium.md",
    ]
    for relative in paths:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise VerificationError(f"required M04 public file is missing or symlinked: {relative}")
        reject_private_text(path.read_text(encoding="utf-8"), relative)


def verify_public(root):
    root = Path(root).resolve()
    verify_baseline(root)
    evidence = load_canonical(root / EVIDENCE_RELATIVE)
    claim_ids = validate_evidence(evidence)
    contract = load_canonical(root / CONTRACT_RELATIVE)
    schema = load_canonical(root / SCHEMA_RELATIVE)
    validate_schema_shape(schema)
    validate_contract_data(contract, claim_ids)
    if contract["evidence_matrix_digest"] != sha256_file(root / EVIDENCE_RELATIVE):
        raise VerificationError("evidence matrix digest mismatch")
    if contract["source_registry_digest"] != sha256_file(root / SOURCE_REGISTER_RELATIVE):
        raise VerificationError("source register digest mismatch")
    validate_sidecar(root)
    validate_public_files(root)
    changed = set(git_text(root, "diff", "--name-only", ACCEPTED_PARENT).splitlines())
    changed.update(git_text(root, "diff", "--cached", "--name-only").splitlines())
    validate_changed_paths(sorted(item for item in changed if item))
    return contract


def source_root():
    override = os.environ.get("PC88VA_PRIVATE_DOCS_ROOT")
    return Path(override).expanduser().resolve() if override else (Path.cwd().resolve().parent / "pc88va-private-docs").resolve()


def count_image_references(text):
    return len(re.findall(r"[^\s\]\)>\"']+\.(?:gif|png|jpe?g|bmp)", text, flags=re.I))


def verify_private_text_evidence(root):
    evidence = load_canonical(root / EVIDENCE_RELATIVE)
    docs = source_root() / "tekumani"
    if not docs.is_dir():
        raise VerificationError("PRIVATE TXT/MARKDOWN SOURCE ROOT IS NOT AVAILABLE")
    grouped = {}
    for claim in evidence["claims"]:
        if claim["claim_type"] not in {"electronic_document_fact", "text_export_fact"}:
            continue
        grouped.setdefault((claim["source_id"], claim["basename"], claim["encoding"]), []).append(claim)
    contextual = (
        ("PRV-TEKUMANI-MAIN-INDEX", "INDEX.TXT", "cp932"),
        ("PRV-VA-KEYB", "603KEYB.TXT", "shift_jisx0213"),
        ("PRV-VA-MISC", "619ETC.TXT", "shift_jisx0213"),
        ("PRV-TSP-EXPORT", "uPD72022.md", "utf-8"),
    )
    for source_id, basename, encoding in contextual:
        grouped.setdefault((source_id, basename, encoding), [])
    records = []
    for (source_id, basename, encoding), claims in sorted(grouped.items()):
        relative = PurePosixPath(basename)
        if relative.is_absolute() or ".." in relative.parts or len(relative.parts) != 1:
            raise VerificationError(f"unsafe private source basename: {basename}")
        path = docs / basename
        if not path.is_file() or path.is_symlink():
            raise VerificationError(f"private source is missing or unsafe: {basename}")
        raw = path.read_bytes()
        text = raw.decode(encoding, errors="replace")
        lines = text.splitlines()
        for claim in claims:
            if claim["line_end"] > len(lines) or not any(lines[claim["line_start"] - 1:claim["line_end"]]):
                raise VerificationError(f"private source locator does not resolve: {claim['claim_id']}")
        records.append({
            "basename": basename,
            "byte_size": len(raw),
            "encoding": encoding,
            "line_count": len(lines),
            "missing_image_reference_count": count_image_references(text),
            "provenance_status": "locally_supplied",
            "replacement_character_count": text.count("\ufffd"),
            "reviewed_sections": sorted({item["section"] for item in claims}) or ["contextual M04 review"],
            "sha256": sha256_bytes(raw),
            "source_id": source_id,
            "source_kind": sorted({item["source_kind"] for item in claims}) or ["contextual_source"],
            "supported_claim_ids": sorted(item["claim_id"] for item in claims),
        })
    result = {"schema_version": 1, "sources": records}
    output = root / "qa/results/m04/private-evidence/source-manifest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes(result))
    return len(records), sum(item["missing_image_reference_count"] for item in records)


def main():
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--private-evidence", action="store_true")
    modes.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    try:
        if args.private_evidence:
            count, missing = verify_private_text_evidence(root)
            print(f"M04 PRIVATE TEXT EVIDENCE PASS: {count} sources; {missing} missing image references recorded without global failure")
        else:
            contract = verify_public(root)
            public = contract["readiness"]["public"]
            print("M04 PUBLIC CONTRACT PASS: " + ", ".join(f"{key}={get_value(public, key)}" for key in sorted(public)))
            print("CI validates the derived public contract and does not inspect private source content.")
    except VerificationError as exc:
        print(f"M04 verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
