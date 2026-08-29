#!/usr/bin/env python3
"""Validate M01 and independently assemble the two M02 bundle runs."""

import argparse
import subprocess
import sys
from pathlib import Path, PurePosixPath

from common import (
    CONSUMER_CONTRACT,
    COPY_METADATA,
    ValidationError,
    archive_epoch_policy,
    artifact_manifest,
    component_identity,
    copy_regular_file,
    create_tar,
    ensure_dir,
    m02_artifacts,
    provenance,
    remove_owned_results,
    validate_host_capability,
    validate_m01_input,
    validate_repository_identity,
    write_canonical_json,
    write_sha256_sidecar,
)


def run_m01_verifier(root):
    run1 = root / "qa/results/m01/run-1"
    run2 = root / "qa/results/m01/run-2"
    if not run1.is_dir() or not run2.is_dir():
        raise ValidationError(
            "verified M01 results are missing; run make m01-image, make m01-build, "
            "make m01-compare, and make m01-verify before running M02"
        )
    command = [sys.executable, str(root / "tools/m01/verify_m01.py"), "--repo-root", str(root)]
    result = subprocess.run(
        command,
        cwd=root,
        env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        output = (result.stdout + result.stderr).strip().replace("\n", " | ")
        raise ValidationError(f"existing M01 verifier rejected the input: {output}")
    print(result.stdout.strip())


def preflight(root):
    validate_host_capability()
    authority = validate_repository_identity(root)
    run_m01_verifier(root)
    validate_m01_input(root / "qa/results/m01/run-1", authority)
    print("M02 preflight passed: parent, component, lock, M01, and host gates are valid")


def assemble_once(root, authority, m01_run, output_run, run_id):
    output_run = Path(output_run)
    if output_run.exists():
        raise ValidationError(f"M02 output already exists; run m02-clean first: {output_run}")
    validate_m01_input(m01_run, authority)
    artifacts = m02_artifacts(authority)
    component_epochs, metadata_epoch = archive_epoch_policy(authority)
    bundle_root = output_run / "baseline-artifact-bundle"
    ensure_dir(bundle_root)
    ensure_dir(bundle_root / "payload")
    ensure_dir(bundle_root / "metadata")
    for item in artifacts:
        source = Path(m01_run) / "artifacts" / PurePosixPath(item["original_m01_source_path"])
        destination = bundle_root / PurePosixPath(item["bundle_path"])
        copy_regular_file(source, destination)
    for bundle_path, source_path, _ in COPY_METADATA:
        copy_regular_file(root / source_path, bundle_root / bundle_path)
    write_canonical_json(
        bundle_root / "metadata/artifact-manifest.json",
        artifact_manifest(root, authority, artifacts, component_epochs, metadata_epoch),
    )
    write_canonical_json(
        bundle_root / "metadata/provenance.json",
        provenance(authority, component_epochs, metadata_epoch),
    )
    write_canonical_json(bundle_root / "metadata/consumer-contract.json", CONSUMER_CONTRACT)
    archive_path = output_run / "baseline-artifact-bundle.tar"
    create_tar(bundle_root, archive_path, artifacts, component_epochs, metadata_epoch)
    write_sha256_sidecar(archive_path, output_run / "baseline-artifact-bundle.tar.sha256")
    try:
        display_path = output_run.relative_to(root)
    except ValueError:
        display_path = output_run
    print(f"M02 assembled {run_id}: {display_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--bundle", action="store_true")
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()
    if sum(bool(value) for value in (args.preflight, args.bundle, args.clean)) != 1:
        parser.error("select exactly one of --preflight, --bundle, or --clean")
    root = args.repo_root.resolve()
    try:
        if args.clean:
            remove_owned_results(root)
            print("M02 generated result paths cleaned")
        elif args.preflight:
            preflight(root)
        else:
            preflight(root)
            authority = component_identity(root)
            m01_run = root / "qa/results/m01/run-1"
            assemble_once(root, authority, m01_run, root / "qa/results/m02/run-1", "run-1")
            assemble_once(root, authority, m01_run, root / "qa/results/m02/run-2", "run-2")
            print("M02 bundle assembly passed")
    except ValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
