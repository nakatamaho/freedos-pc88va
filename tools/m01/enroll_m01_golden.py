#!/usr/bin/env python3
"""Explicitly enroll a previously passing M01 comparison as the golden."""

import argparse
import json
from pathlib import Path


def load(path):
    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run1", type=Path, required=True)
    parser.add_argument("--run2", type=Path, required=True)
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--golden", type=Path, required=True)
    args = parser.parse_args()

    comparison = load(args.comparison)
    if comparison.get("status") != "pass" or comparison.get("byte_identical") is not True or comparison.get("errors") != []:
        raise SystemExit("error: refusing golden enrollment because the comparison did not pass")
    first = load(args.run1 / "manifest.json")
    second = load(args.run2 / "manifest.json")
    comparable_fields = set(first) | set(second)
    comparable_fields.discard("run_id")
    if any(first.get(field) != second.get(field) for field in comparable_fields):
        raise SystemExit("error: refusing golden enrollment because non-run identity fields differ")
    required = ("milestone", "canonical_platform", "contract_sha256", "toolchain_lock_sha256", "source_archives", "artifacts")
    if any(field not in first for field in required):
        raise SystemExit("error: refusing golden enrollment because run-1 manifest is incomplete")

    golden = {
        "schema_version": 1,
        "milestone": first["milestone"],
        "canonical_platform": first["canonical_platform"],
        "contract_sha256": first["contract_sha256"],
        "toolchain_lock_sha256": first["toolchain_lock_sha256"],
        "source_archives": first["source_archives"],
        "artifacts": first["artifacts"],
        "comparison": "byte-identical",
        "informational_country_comparison": comparison["informational_country_comparison"],
    }
    args.golden.parent.mkdir(parents=True, exist_ok=True)
    with args.golden.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(golden, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print("M01 golden enrollment passed: committed golden was explicitly replaced from a passing comparison")


if __name__ == "__main__":
    main()
