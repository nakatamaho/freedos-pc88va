#!/usr/bin/env python3
"""Compare two complete M02 bundle trees and archives byte-for-byte."""

import argparse
import json
import sys
from pathlib import Path

from common import ValidationError, canonical_json_bytes, compare_tree_roots, sha256_file, tree_entries


def file_observation(path):
    return {"size": path.stat().st_size, "sha256": sha256_file(path)}


def compare_file(first, second, label, errors):
    if not first.is_file() or not second.is_file():
        errors.append({"type": "missing-file", "label": label, "run_1": first.is_file(), "run_2": second.is_file()})
        return None
    first_observation = file_observation(first)
    second_observation = file_observation(second)
    if first_observation != second_observation:
        errors.append({"type": "file-byte-mismatch", "label": label, "run_1": first_observation, "run_2": second_observation})
    return first_observation, second_observation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run1", type=Path, default=Path("qa/results/m02/run-1"))
    parser.add_argument("--run2", type=Path, default=Path("qa/results/m02/run-2"))
    parser.add_argument("--output", type=Path, default=Path("qa/results/m02/comparison.json"))
    args = parser.parse_args()
    errors = []
    try:
        errors.extend(compare_tree_roots(args.run1 / "baseline-artifact-bundle", args.run2 / "baseline-artifact-bundle"))
        archive_observation = compare_file(args.run1 / "baseline-artifact-bundle.tar", args.run2 / "baseline-artifact-bundle.tar", "tar", errors)
        sidecar_observation = compare_file(args.run1 / "baseline-artifact-bundle.tar.sha256", args.run2 / "baseline-artifact-bundle.tar.sha256", "tar-sha256-sidecar", errors)
        result = {
            "schema_version": 1,
            "milestone": "M02-baseline-artifact-bundle",
            "run_1": "run-1",
            "run_2": "run-2",
            "tree_byte_identical": not any(error["type"] in {"path-set-mismatch", "entry-type-mismatch", "file-byte-mismatch"} for error in errors),
            "archive_byte_identical": bool(archive_observation and archive_observation[0] == archive_observation[1]),
            "sidecar_byte_identical": bool(sidecar_observation and sidecar_observation[0] == sidecar_observation[1]),
            "run_1_tar": archive_observation[0] if archive_observation else None,
            "run_2_tar": archive_observation[1] if archive_observation else None,
            "run_1_sidecar": sidecar_observation[0] if sidecar_observation else None,
            "run_2_sidecar": sidecar_observation[1] if sidecar_observation else None,
            "errors": errors,
        }
        result["byte_identical"] = result["tree_byte_identical"] and result["archive_byte_identical"] and result["sidecar_byte_identical"]
        result["status"] = "pass" if result["byte_identical"] and not errors else "fail"
    except (ValidationError, OSError) as exc:
        result = {
            "schema_version": 1,
            "milestone": "M02-baseline-artifact-bundle",
            "byte_identical": False,
            "status": "fail",
            "errors": [{"type": "validation-error", "message": str(exc)}],
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json_bytes(result))
    if result["status"] != "pass":
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1
    print("M02 comparison passed: trees, tar archives, and sidecars are byte-identical")
    print(json.dumps({"run_1_tar": result.get("run_1_tar"), "run_2_tar": result.get("run_2_tar")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
