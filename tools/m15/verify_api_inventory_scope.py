#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Verify the fixed M15 FreeDOS service-test boundary and issue deferrals."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "config/m15/api-inventory.json"
SCOPE_ID = "M15-API-SCOPE-FREEDOS-VA-v4"
TARGET = "Selected FreeDOS kernel and FreeCOM port for PC-88VA; MS-DOS references provide historical context and are not behavior-matching requirements"
SOURCE_BASELINE = {
    "fdkernel": "ac16c8a7401526f99787e03babdb2f4223d48fc4",
    "freecom": "9cf57b28abf1d98fab7655fb811375a2aa16c6d9",
}
EXPECTED_ROWS = 221
EXPECTED_DISPOSITIONS = {
    "REQUIRED": 113,
    "OUT_OF_PROFILE": 82,
    "UNDOCUMENTED_OBSERVATION": 26,
}
EXPECTED_ALL_IDS_SHA256 = "6abf7ebcad90f74e5b3183a91e04184deb79ca638ec89471b26a020be364cabf"
EXPECTED_REQUIRED_IDS_SHA256 = "62b20a19635d2f8a93f01d8334a8324671fb2e15993bbcd2ede7b2885f483663"
EXPECTED_DEFERRED_REFERENCE_IDS = {
    "21-1F",
    "21-32",
    "21-3A",
    "21-63-AL_00",
    "25-CXnot_FFFF",
    "26-CXnot_FFFF",
}
EXPECTED_DEFERRED_REFERENCE_IDS_SHA256 = "12b7db34933d212a436b802b697bd7b1638486db70860e79b243aa472cfa5ca3"
EXPECTED_FORMAT_VERSION = 3
PUBLIC_RESULT_POLICY = (
    "This public scope ledger omits per-case outcomes and concrete observations. "
    "Retain private-run results only in excluded local evidence; publish only "
    "reviewed, permitted aggregate status."
)


def sorted_id_digest(ids):
    payload = "".join(value + "\n" for value in sorted(ids))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify(data):
    lock = data["scope_lock"]
    rows = data["rows"]
    ids = [row["id"] for row in rows]
    tuples = [
        (row["interrupt"], row["function"], row["subfunction"])
        for row in rows
    ]
    dispositions = {
        name: sum(row["disposition"] == name for row in rows)
        for name in ("REQUIRED", "OUT_OF_PROFILE", "UNDOCUMENTED_OBSERVATION")
    }
    errors = []

    if data.get("format_version") != EXPECTED_FORMAT_VERSION:
        errors.append("API inventory format version changed without updating the verifier")
    if data.get("public_result_policy") != PUBLIC_RESULT_POLICY:
        errors.append("public per-case evidence policy changed")
    if lock["id"] != SCOPE_ID:
        errors.append("scope lock ID changed")
    if lock.get("target") != TARGET:
        errors.append("API target or runtime-version policy changed")
    if data.get("source_baseline") != SOURCE_BASELINE:
        errors.append("pinned source baseline changed without a reviewed boundary amendment")
    if "dispatch-entry test-boundary ID" not in lock.get("contract_unit", ""):
        errors.append("inventory unit must remain a dispatch-entry boundary ID")
    if "not a separate behavioral contract" not in lock.get("contract_unit", ""):
        errors.append("inventory rows must not be presented as a count of behavioral contracts")
    if "MS-DOS-only differences do not create defects or changes" not in lock.get("membership_rule", ""):
        errors.append("MS-DOS-only differences must remain outside the port acceptance rule")
    if lock["boundary_document"] != "docs/porting/m15-api-boundary.md":
        errors.append("scope boundary document changed")
    if len(rows) != EXPECTED_ROWS or lock["row_count"] != EXPECTED_ROWS:
        errors.append(f"row count is {len(rows)}, expected {EXPECTED_ROWS}")
    if len(set(ids)) != len(ids):
        errors.append("duplicate inventory ID")
    if len(set(tuples)) != len(tuples):
        errors.append("duplicate interrupt/function/subfunction tuple")
    if dispositions != lock["disposition_counts"]:
        errors.append(f"disposition counts differ: {dispositions}")
    if dispositions != EXPECTED_DISPOSITIONS:
        errors.append(f"scope classifications differ from the locked V3 boundary: {dispositions}")
    if sorted_id_digest(ids) != EXPECTED_ALL_IDS_SHA256:
        errors.append("inventory ID set changed without a scope amendment")
    if lock["all_ids_sha256_sorted_lf"] != EXPECTED_ALL_IDS_SHA256:
        errors.append("locked inventory digest changed without a scope amendment")
    required_ids = [row["id"] for row in rows if row["disposition"] == "REQUIRED"]
    if sorted_id_digest(required_ids) != EXPECTED_REQUIRED_IDS_SHA256:
        errors.append("required FreeDOS service set changed without a scope amendment")
    if lock["required_ids_sha256_sorted_lf"] != EXPECTED_REQUIRED_IDS_SHA256:
        errors.append("locked required-service digest changed without a scope amendment")

    deferred_reference_rows = [
        row for row in rows if row.get("deferred_reference_review") is not None
    ]
    deferred_reference_ids = {row["id"] for row in deferred_reference_rows}
    if deferred_reference_ids != EXPECTED_DEFERRED_REFERENCE_IDS:
        errors.append(
            "deferred MS-DOS reference-question IDs changed: "
            f"{sorted(deferred_reference_ids)}"
        )
    if lock.get("deferred_reference_review_count") != len(EXPECTED_DEFERRED_REFERENCE_IDS):
        errors.append("deferred reference-question count changed")
    if sorted_id_digest(deferred_reference_ids) != EXPECTED_DEFERRED_REFERENCE_IDS_SHA256:
        errors.append("deferred reference-question IDs changed without an amendment")
    if lock.get("deferred_reference_ids_sha256_sorted_lf") != EXPECTED_DEFERRED_REFERENCE_IDS_SHA256:
        errors.append("locked deferred reference-question digest changed")
    for row in deferred_reference_rows:
        review = row["deferred_reference_review"]
        if review.get("status") != "DEFERRED_M15_PLUS" or review.get("outcome") != "NOT_RUN":
            errors.append(f"{row['id']}: deferred reference review must be DEFERRED_M15_PLUS/NOT_RUN")
        if not review.get("issue", "").startswith("https://github.com/nakatamaho/freedos-pc88va/issues/"):
            errors.append(f"{row['id']}: deferred reference review lacks a parent issue")

    known_references = data["references"]
    for row in rows:
        if "contract_status" in row or "port_review_status" not in row:
            errors.append(f"{row['id']}: use port_review_status, not a compatibility-contract status")
        if "outcome" in row or "observation_record" in row:
            errors.append(f"{row['id']}: private per-case outcomes must not be published in the scope ledger")
        if row.get("port_review_status", "").startswith("TARGET_VERSION_EXCLUDED"):
            errors.append(f"{row['id']}: exclusions must describe the selected M15 feature profile")
        for reference in row["specification"].get("references", []):
            if reference not in known_references and not reference.startswith(("https://", "http://")):
                errors.append(f"{row['id']}: unknown reference key {reference}")

    if errors:
        raise ValueError("; ".join(errors))
    return {
        "scope": lock["id"],
        "rows": len(rows),
        "required_services": dispositions["REQUIRED"],
        "deferred_reference_questions": len(deferred_reference_ids),
        "out_of_profile": dispositions["OUT_OF_PROFILE"],
        "undocumented_observations": dispositions["UNDOCUMENTED_OBSERVATION"],
        "status": "PASS",
    }


def main():
    result = verify(json.loads(INVENTORY.read_text(encoding="utf-8")))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
