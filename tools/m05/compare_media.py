#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Compare two independently generated M05 result trees byte-for-byte."""

from __future__ import annotations

import argparse
import os
import stat
import sys
from pathlib import Path

from common import ValidationError, sha256_file, write_canonical_json


def tree_snapshot(root: Path) -> list[dict]:
    if root.is_symlink() or not root.is_dir():
        raise ValidationError(f"M05 run tree is missing or unsafe: {root}")
    records = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise ValidationError(f"symlink in M05 run tree: {relative}")
        if stat.S_ISDIR(info.st_mode):
            records.append({"path": relative, "type": "directory"})
        elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
            records.append({"path": relative, "sha256": sha256_file(path), "size": info.st_size, "type": "file"})
        else:
            raise ValidationError(f"unsupported or hard-linked M05 run entry: {relative}")
    return records


def compare_runs(run1: Path, run2: Path) -> dict:
    first = tree_snapshot(run1)
    second = tree_snapshot(run2)
    errors = []
    first_by_path = {item["path"]: item for item in first}
    second_by_path = {item["path"]: item for item in second}
    if set(first_by_path) != set(second_by_path):
        errors.append({
            "extra_in_run_2": sorted(set(second_by_path) - set(first_by_path)),
            "missing_in_run_2": sorted(set(first_by_path) - set(second_by_path)),
            "type": "path_set_mismatch",
        })
    for relative in sorted(set(first_by_path) & set(second_by_path)):
        if first_by_path[relative] != second_by_path[relative]:
            errors.append({"path": relative, "run_1": first_by_path[relative], "run_2": second_by_path[relative], "type": "entry_mismatch"})
        elif first_by_path[relative]["type"] == "file":
            if (run1 / relative).read_bytes() != (run2 / relative).read_bytes():
                errors.append({"path": relative, "type": "byte_mismatch"})
    return {
        "byte_identical": not errors,
        "errors": errors,
        "milestone": "M05-deterministic-candidate-media",
        "run_1": first,
        "run_2": second,
        "schema_version": 1,
        "status": "pass" if not errors else "fail",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-1", type=Path, default=Path("qa/results/m05/run-1"))
    parser.add_argument("--run-2", type=Path, default=Path("qa/results/m05/run-2"))
    parser.add_argument("--output", type=Path, default=Path("qa/results/m05/comparison.json"))
    args = parser.parse_args()
    try:
        result = compare_runs(args.run_1, args.run_2)
        write_canonical_json(args.output, result)
    except (OSError, ValidationError) as exc:
        print(f"M05 comparison failed: {exc}", file=sys.stderr)
        return 1
    if result["status"] != "pass":
        print(f"M05 comparison failed: {result['errors']}", file=sys.stderr)
        return 1
    print("M05 comparison passed: complete run trees are byte-identical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
