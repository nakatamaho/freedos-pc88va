#!/usr/bin/env python3
"""Compare two M01 artifact manifests and optionally create the golden manifest."""

import argparse
import hashlib
import json
from pathlib import Path


def load_json(path):
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def bounded_byte_difference(first, second, maximum_ranges=16, maximum_range_width=128):
    first_size = first.stat().st_size
    second_size = second.stat().st_size
    common_size = min(first_size, second_size)
    ranges = []
    first_offset = None
    pending_start = None
    pending_end = None
    offset = 0
    with first.open("rb") as first_stream, second.open("rb") as second_stream:
        while offset < common_size:
            first_block = first_stream.read(1024 * 1024)
            second_block = second_stream.read(1024 * 1024)
            for index, (first_byte, second_byte) in enumerate(zip(first_block, second_block)):
                if first_byte == second_byte:
                    if pending_start is not None:
                        ranges.append([pending_start, pending_end])
                        pending_start = None
                        pending_end = None
                    continue
                absolute = offset + index
                if first_offset is None:
                    first_offset = absolute
                if pending_start is None:
                    pending_start = absolute
                    pending_end = absolute + 1
                elif absolute - pending_start < maximum_range_width:
                    pending_end = absolute + 1
                else:
                    ranges.append([pending_start, pending_end])
                    pending_start = absolute
                    pending_end = absolute + 1
                if len(ranges) >= maximum_ranges:
                    break
            offset += len(first_block)
            if len(ranges) >= maximum_ranges:
                break
    if pending_start is not None and len(ranges) < maximum_ranges:
        ranges.append([pending_start, pending_end])
    if first_offset is None and first_size != second_size:
        first_offset = common_size
        if len(ranges) < maximum_ranges:
            ranges.append([common_size, max(first_size, second_size)])
    return {
        "first_differing_byte": first_offset,
        "differing_ranges": ranges[:maximum_ranges],
        "ranges_truncated": len(ranges) > maximum_ranges,
    }


def country_observation(first_records, second_records):
    names = ["fdkernel-country/nec98/bin/country.sys", "fdos-country/country.sys"]
    observation = {"comparison": "informational", "artifacts": []}
    for name in names:
        first = first_records.get(name)
        second = second_records.get(name)
        record = {"artifact": name, "present_in_both_runs": bool(first and second)}
        if first and second:
            record.update(
                {
                    "run_1_sha256": first["sha256"],
                    "run_2_sha256": second["sha256"],
                    "run_1_size": first["size"],
                    "run_2_size": second["size"],
                }
            )
        observation["artifacts"].append(record)
    first = first_records.get(names[0])
    second = first_records.get(names[1])
    observation["equal_within_run_1"] = bool(first and second and first["sha256"] == second["sha256"] and first["size"] == second["size"])
    return observation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run1", type=Path, required=True)
    parser.add_argument("--run2", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--golden", type=Path)
    args = parser.parse_args()

    first = load_json(args.run1 / "manifest.json")
    second = load_json(args.run2 / "manifest.json")
    errors = []
    identity_keys = [
        "milestone",
        "canonical_platform",
        "contract_sha256",
        "toolchain_lock_sha256",
        "source_archives",
    ]
    for key in identity_keys:
        if first.get(key) != second.get(key):
            errors.append({"type": "identity-mismatch", "field": key, "run_1": first.get(key), "run_2": second.get(key)})

    first_records = {record["artifact"]: record for record in first.get("artifacts", [])}
    second_records = {record["artifact"]: record for record in second.get("artifacts", [])}
    first_names = set(first_records)
    second_names = set(second_records)
    for name in sorted(first_names - second_names):
        errors.append({"type": "missing-artifact", "run": "run-2", "artifact": name})
    for name in sorted(second_names - first_names):
        errors.append({"type": "extra-artifact", "run": "run-2", "artifact": name})

    for name in sorted(first_names & second_names):
        first_record = first_records[name]
        second_record = second_records[name]
        for field in ("component_commit", "source_archive_sha256"):
            if first_record.get(field) != second_record.get(field):
                errors.append({"type": "artifact-identity-mismatch", "artifact": name, "field": field, "run_1": first_record.get(field), "run_2": second_record.get(field)})
        if first_record.get("size") != second_record.get("size") or first_record.get("sha256") != second_record.get("sha256"):
            first_path = args.run1 / "artifacts" / name
            second_path = args.run2 / "artifacts" / name
            difference = bounded_byte_difference(first_path, second_path)
            errors.append(
                {
                    "type": "byte-mismatch",
                    "artifact": name,
                    "run_1_sha256": first_record.get("sha256"),
                    "run_2_sha256": second_record.get("sha256"),
                    "run_1_size": first_record.get("size"),
                    "run_2_size": second_record.get("size"),
                    **difference,
                }
            )

    result = {
        "schema_version": 1,
        "milestone": first.get("milestone"),
        "run_1": first.get("run_id"),
        "run_2": second.get("run_id"),
        "contract_sha256": first.get("contract_sha256"),
        "toolchain_lock_sha256": first.get("toolchain_lock_sha256"),
        "source_archives": first.get("source_archives"),
        "byte_identical": not errors,
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "informational_country_comparison": country_observation(first_records, second_records),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")

    if errors:
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit("error: M01 required artifacts are not byte-reproducible")

    if args.golden:
        golden = {
            "schema_version": 1,
            "milestone": first["milestone"],
            "canonical_platform": first["canonical_platform"],
            "contract_sha256": first["contract_sha256"],
            "toolchain_lock_sha256": first["toolchain_lock_sha256"],
            "source_archives": first["source_archives"],
            "artifacts": first["artifacts"],
            "comparison": "byte-identical",
            "informational_country_comparison": result["informational_country_comparison"],
        }
        args.golden.parent.mkdir(parents=True, exist_ok=True)
        with args.golden.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(golden, stream, indent=2, sort_keys=True)
            stream.write("\n")
    print(f"M01 comparison passed: {len(first_records)} required artifacts are byte-identical")


if __name__ == "__main__":
    main()
