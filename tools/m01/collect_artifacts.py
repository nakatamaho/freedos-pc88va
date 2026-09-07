#!/usr/bin/env python3
"""Collect the declared M01 artifacts into a deterministic JSON manifest."""

import argparse
import hashlib
import json
import os
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


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def fail(message):
    raise SystemExit(f"error: {message}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--toolchains", type=Path, required=True)
    parser.add_argument("--source-archives", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    contract = load_json(args.contract)
    toolchains = load_json(args.toolchains)
    source_archives = load_json(args.source_archives)
    run_id = args.run_dir.name
    if run_id not in {"run-1", "run-2"}:
        fail(f"unexpected run directory: {run_id}")

    contract_digest = sha256_file(args.contract)
    toolchain_digest = sha256_file(args.toolchains)
    components = contract.get("components")
    if not isinstance(components, list) or len(components) != 3:
        fail("the build contract must contain exactly three components")

    expected = {}
    for component in components:
        name = component.get("name")
        source_name = Path(component.get("path", "")).name
        commit = component.get("commit")
        archive_digest = source_archives.get(source_name)
        if not isinstance(name, str) or not isinstance(commit, str):
            fail("component identity is incomplete")
        if not isinstance(archive_digest, str) or len(archive_digest) != 64:
            fail(f"source archive digest is missing for {source_name}")
        for artifact in component.get("required_artifacts", []):
            namespace = artifact.get("namespace")
            relative_path = artifact.get("path")
            if not namespace or not relative_path:
                fail(f"incomplete required artifact in {name}")
            artifact_name = f"{namespace}/{relative_path}"
            if artifact_name in expected:
                fail(f"duplicate required artifact: {artifact_name}")
            expected[artifact_name] = {
                "component_commit": commit,
                "source_archive_sha256": archive_digest,
            }

    artifact_root = args.run_dir / "artifacts"
    if not artifact_root.is_dir():
        fail(f"artifact directory is missing: {artifact_root}")
    actual = []
    for root, directories, files in os.walk(artifact_root):
        directories.sort()
        files.sort()
        for filename in files:
            path = Path(root) / filename
            actual.append(path.relative_to(artifact_root).as_posix())
    actual_set = set(actual)
    expected_set = set(expected)
    if actual_set != expected_set:
        missing = sorted(expected_set - actual_set)
        extra = sorted(actual_set - expected_set)
        fail(f"artifact set mismatch: missing={missing}, extra={extra}")

    records = []
    for artifact_name in sorted(expected):
        path = artifact_root / artifact_name
        if not path.is_file() or path.stat().st_size == 0:
            fail(f"required artifact is missing or empty: {artifact_name}")
        metadata = expected[artifact_name]
        records.append(
            {
                "artifact": artifact_name,
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
                "component_commit": metadata["component_commit"],
                "build_contract_sha256": contract_digest,
                "toolchain_lock_sha256": toolchain_digest,
                "source_archive_sha256": metadata["source_archive_sha256"],
            }
        )

    manifest = {
        "schema_version": 1,
        "milestone": contract["milestone"],
        "run_id": run_id,
        "canonical_platform": contract["canonical_platform"],
        "contract_sha256": contract_digest,
        "toolchain_lock_sha256": toolchain_digest,
        "source_archives": {key: source_archives[key] for key in sorted(source_archives)},
        "artifact_count": len(records),
        "artifacts": records,
    }
    del toolchains
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"collected {len(records)} required artifacts for {run_id}")


if __name__ == "__main__":
    main()
