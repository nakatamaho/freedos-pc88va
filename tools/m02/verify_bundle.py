#!/usr/bin/env python3
"""Verify M02 bundle contents, archive attributes, and golden enrollment."""

import argparse
import hashlib
import sys
import tarfile
from pathlib import Path, PurePosixPath

from common import (
    M01R1_COMMITTED_DIGESTS,
    CONSUMER_CONTRACT,
    COPY_METADATA,
    GENERATED_METADATA,
    ValidationError,
    archive_epoch_policy,
    archive_mtime_for,
    artifact_manifest,
    canonical_json_bytes,
    component_identity,
    expected_bundle_paths,
    lstat_checked,
    load_canonical_json,
    m02_artifacts,
    provenance,
    reject_generated_metadata_values,
    sha256_file,
    snapshot_for_golden,
    tree_entries,
    validate_artifact_contract_records,
    validate_host_capability,
    validate_m01_input,
    validate_repository_identity,
    write_canonical_json,
)


def validate_tar(run_root, artifacts, component_epochs, metadata_epoch, expected_paths):
    run_root = Path(run_root)
    archive_path = run_root / "baseline-artifact-bundle.tar"
    sidecar_path = run_root / "baseline-artifact-bundle.tar.sha256"
    lstat_checked(archive_path, "tar archive")
    lstat_checked(sidecar_path, "tar sidecar")
    expected_sidecar = f"{sha256_file(archive_path)}  {archive_path.name}\n".encode("ascii")
    if sidecar_path.read_bytes() != expected_sidecar:
        raise ValidationError("tar SHA-256 sidecar is not canonical or does not match the archive")
    try:
        with archive_path.open("rb") as raw_archive:
            first_header = raw_archive.read(512)
        if first_header[257:265] != b"ustar\x0000":
            raise ValidationError("tar archive is not POSIX USTAR format")
    except OSError as exc:
        raise ValidationError(f"cannot read tar header: {exc}") from exc
    try:
        with tarfile.open(archive_path, mode="r:") as archive:
            members = archive.getmembers()
            names = [member.name for member in members]
            if len(names) != len(set(names)):
                raise ValidationError("tar archive contains duplicate entry names")
            if set(names) != expected_paths:
                raise ValidationError(
                    f"tar path set mismatch: missing={sorted(expected_paths - set(names))}, "
                    f"extra={sorted(set(names) - expected_paths)}"
                )
            for member in members:
                if not member.name.isascii() or member.pax_headers:
                    raise ValidationError(f"tar entry has unsafe name or PAX headers: {member.name!r}")
                safe_name = PurePosixPath(member.name)
                if safe_name.is_absolute() or ".." in safe_name.parts:
                    raise ValidationError(f"tar entry path traversal: {member.name!r}")
                if member.uid != 0 or member.gid != 0 or member.uname != "" or member.gname != "":
                    raise ValidationError(f"tar ownership is not canonical: {member.name}")
                if member.mtime != archive_mtime_for(member.name, artifacts, component_epochs, metadata_epoch):
                    raise ValidationError(f"tar mtime is not canonical: {member.name}")
                if member.isdir():
                    if (member.mode & 0o7777) != 0o755 or member.size != 0:
                        raise ValidationError(f"tar directory attributes are not canonical: {member.name}")
                elif member.isreg():
                    if (member.mode & 0o7777) != 0o644:
                        raise ValidationError(f"tar file mode is not canonical: {member.name}")
                    expected_file = run_root / PurePosixPath(member.name)
                    if member.size != expected_file.stat().st_size:
                        raise ValidationError(f"tar file size mismatch: {member.name}")
                    stream = archive.extractfile(member)
                    if stream is None:
                        raise ValidationError(f"tar regular file cannot be read: {member.name}")
                    digest = hashlib.sha256()
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(block)
                    if digest.hexdigest() != sha256_file(expected_file):
                        raise ValidationError(f"tar bytes mismatch: {member.name}")
                else:
                    raise ValidationError(f"tar contains a non-regular entry: {member.name}")
    except (OSError, tarfile.TarError) as exc:
        raise ValidationError(f"cannot inspect M02 tar archive: {exc}") from exc


def validate_bundle(root, authority, run_root, m01_run):
    run_root = Path(run_root)
    bundle_root = run_root / "baseline-artifact-bundle"
    artifacts = m02_artifacts(authority)
    validate_artifact_contract_records(artifacts)
    expected_paths = expected_bundle_paths(artifacts)
    actual_entries = tree_entries(bundle_root)
    actual_paths = {entry[0] for entry in actual_entries}
    if actual_paths != expected_paths:
        raise ValidationError(
            f"M02 bundle path set mismatch: missing={sorted(expected_paths - actual_paths)}, "
            f"extra={sorted(actual_paths - expected_paths)}"
        )
    for relative, entry_type, _, _ in actual_entries:
        path = run_root / PurePosixPath(relative)
        info = lstat_checked(path, "bundle entry")
        if entry_type == "directory" and not info.st_mode & 0o40000:
            raise ValidationError(f"bundle entry is not a directory: {relative}")
        if entry_type == "file" and (not info.st_mode & 0o100000 or (info.st_mode & 0o777) != 0o644):
            raise ValidationError(f"bundle file mode or type mismatch: {relative}")

    validate_m01_input(m01_run, authority)
    component_epochs, metadata_epoch = archive_epoch_policy(authority)
    manifest = load_canonical_json(bundle_root / "metadata/artifact-manifest.json")
    provenance_data = load_canonical_json(bundle_root / "metadata/provenance.json")
    consumer = load_canonical_json(bundle_root / "metadata/consumer-contract.json")
    for value, label in ((manifest, "artifact-manifest"), (provenance_data, "provenance"), (consumer, "consumer-contract")):
        reject_generated_metadata_values(value, label)
    expected_manifest = artifact_manifest(root, authority, artifacts, component_epochs, metadata_epoch)
    if manifest != expected_manifest:
        raise ValidationError("artifact-manifest.json does not match the M01 golden and contract")
    if provenance_data != provenance(authority, component_epochs, metadata_epoch):
        raise ValidationError("provenance.json does not match the committed source identity")
    if consumer != CONSUMER_CONTRACT:
        raise ValidationError("consumer-contract.json does not match the M02 role contract")

    for bundle_path, source_path, digest_name in COPY_METADATA:
        source = root / source_path
        destination = bundle_root / bundle_path
        if destination.read_bytes() != source.read_bytes() or sha256_file(destination) != M01R1_COMMITTED_DIGESTS[digest_name]:
            raise ValidationError(f"copied committed metadata was modified: {bundle_path}")
    for item in artifacts:
        destination = bundle_root / item["bundle_path"]
        if destination.stat().st_size != item["size"] or sha256_file(destination) != item["sha256"]:
            raise ValidationError(f"payload identity mismatch: {item['bundle_path']}")
    country = [item for item in artifacts if PurePosixPath(item["original_m01_source_path"]).name.lower() == "country.sys"]
    if len(country) != 2 or country[0]["sha256"] == country[1]["sha256"]:
        raise ValidationError("the two COUNTRY.SYS payloads must remain distinct")
    validate_tar(run_root, artifacts, component_epochs, metadata_epoch, expected_paths)
    return snapshot_for_golden(run_root, artifacts)


def check_comparison(path):
    if not Path(path).is_file():
        raise ValidationError("M02 comparison evidence is missing; run make m02-compare first")
    comparison = load_canonical_json(path)
    if comparison.get("status") != "pass" or comparison.get("byte_identical") is not True:
        raise ValidationError("M02 comparison evidence is not a passing byte-identical result")


def verify(root, authority, run1, run2, golden_path, comparison_path, m01_run):
    if not Path(golden_path).is_file():
        raise ValidationError("M02 golden is missing; use the explicit --enroll-golden command after comparison")
    check_comparison(comparison_path)
    first = validate_bundle(root, authority, run1, m01_run)
    second = validate_bundle(root, authority, run2, m01_run)
    golden = load_canonical_json(golden_path)
    if first != second:
        raise ValidationError("run-1 and run-2 bundle snapshots differ")
    if golden != first:
        raise ValidationError("M02 result does not match the committed golden manifest")
    print("M02 verification passed: payloads, role metadata, provenance, tar attributes, and golden are valid")


def enroll(root, authority, run1, run2, golden_path, comparison_path, m01_run, supersede=False):
    if Path(golden_path).exists() and not supersede:
        raise ValidationError(f"M02 golden already exists; ordinary verification never rewrites it: {golden_path}")
    check_comparison(comparison_path)
    first = validate_bundle(root, authority, run1, m01_run)
    second = validate_bundle(root, authority, run2, m01_run)
    if first != second:
        raise ValidationError("cannot enroll M02 golden when run-1 and run-2 differ")
    if supersede:
        print(f"M02 golden superseded explicitly: {golden_path}")
    write_canonical_json(golden_path, first)
    print(f"M02 golden enrolled explicitly: {golden_path}")
    print(f"M02 golden SHA-256: {sha256_file(golden_path)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--enroll-golden", action="store_true")
    parser.add_argument("--supersede-golden", action="store_true")
    parser.add_argument("--run1", type=Path, default=Path("qa/results/m02/run-1"))
    parser.add_argument("--run2", type=Path, default=Path("qa/results/m02/run-2"))
    parser.add_argument("--golden", type=Path, default=Path("qa/golden/m02/bundle-manifest.json"))
    parser.add_argument("--comparison", type=Path, default=Path("qa/results/m02/comparison.json"))
    args = parser.parse_args()
    root = args.repo_root.resolve()
    def rooted(path):
        return path if path.is_absolute() else root / path
    try:
        validate_host_capability()
        authority = validate_repository_identity(root)
        m01_run = root / "qa/results/m01/run-1"
        if args.supersede_golden and not args.enroll_golden:
            parser.error("--supersede-golden requires --enroll-golden")
        if args.enroll_golden:
            enroll(root, authority, rooted(args.run1), rooted(args.run2), rooted(args.golden), rooted(args.comparison), m01_run, args.supersede_golden)
        else:
            verify(root, authority, rooted(args.run1), rooted(args.run2), rooted(args.golden), rooted(args.comparison), m01_run)
    except ValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
