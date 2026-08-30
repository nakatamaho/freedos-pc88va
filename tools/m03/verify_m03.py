#!/usr/bin/env python3
"""Verify M03 baseline identity, census schema, determinism, and golden data."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

from scan_port_surface import (
    BASELINE_PARENT_COMMIT,
    CLASSIFICATIONS,
    DISPOSITIONS,
    MECHANISMS,
    PLATFORMS,
    RULES,
    SCANNER_NAME,
    SCANNER_VERSION,
    SURFACES,
    TARGET_MILESTONES,
    canonical_json_bytes,
    counts,
    ruleset_descriptors,
    ruleset_sha256,
)


M01_COMPONENTS_LOCK_SHA256 = "440e481b28c740875489a6953a246ce5370c44074053c7aad3f80e79ec40c19c"
M01_TOOLCHAIN_LOCK_SHA256 = "39c5b3052d71463235a26e8704ab54c1fedb51ee75bb4efb55e6229391a95162"
M01_BUILD_CONTRACT_SHA256 = "7d66be32b508395d8c36a902389f368e9f38d9abab08085bda89e3d2c5d6d578"
M01_GOLDEN_SHA256 = "6fcfe834f90ffc602589ddc63b50d90eba33bbc1802b6bff3c9ef6b9d397c7c3"
M02_GOLDEN_SHA256 = "4d4e92f92911130109b5b140b2202fc1dfc3abb9af3cd7501b685894d0cb78fd"
M02_TAR_SIZE = 399360
M02_TAR_SHA256 = "00fb02b03ea16423b5987d455a8ea11a8a567c699484656228722119c6239e51"
M02_SIDECAR_SHA256 = "0ffe8a10fd1c430fc876a7387e44fe6084be5b21deaf93bb8826a3b13b278fbb"
PARENT_REPOSITORY = "https://github.com/nakatamaho/freedos-pc88va.git"
M03_BRANCH = "topic/m03-port-surface-adr"
M03_MILESTONE = "M03-port-surface-census-and-integration-adr"

PROTECTED_PATHS = (
    ".gitmodules",
    "components/fdkernel",
    "components/freecom",
    "components/country",
    "containers/m01",
    ".github/workflows/m01-baseline.yml",
    ".github/workflows/m02-bundle.yml",
    "tools/m01",
    "tools/m02",
    "manifests/components.lock.json",
    "manifests/toolchains.lock.json",
    "manifests/m01-build-contract.json",
    "qa/golden/m01-baseline.json",
    "qa/golden/m02/bundle-manifest.json",
)

REQUIRED_ENTRY_FIELDS = (
    "id",
    "component",
    "component_commit",
    "platform",
    "path",
    "symbol_or_section",
    "surface",
    "mechanism",
    "matched_rule",
    "evidence_excerpt_or_token",
    "classification",
    "candidate_boundary",
    "disposition",
    "confidence",
    "target_milestone",
    "notes",
)
ABSOLUTE_PATH = re.compile(r"^(?:/|[A-Za-z]:[\\/])")
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T ][0-9]{2}:[0-9]{2})")
UNSTABLE_KEYS = {
    "generated_at",
    "created_at",
    "updated_at",
    "timestamp",
    "hostname",
    "username",
    "user_name",
    "cwd",
    "working_directory",
    "absolute_path",
    "container_id",
    "docker_context",
    "image_id",
}
PRIVATE_OR_BINARY_SUFFIXES = {
    ".rom",
    ".d88",
    ".d98",
    ".hdi",
    ".hdd",
    ".img",
    ".ima",
    ".iso",
    ".bin",
    ".sys",
    ".com",
    ".obj",
    ".o",
    ".a",
    ".lib",
    ".tar",
    ".gz",
    ".zip",
    ".log",
}


class VerificationError(Exception):
    """A bounded fail-closed M03 verification error."""


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes())


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"cannot parse JSON {path}: {exc}") from exc


def load_canonical(path):
    path = Path(path)
    value = load_json(path)
    if path.read_bytes() != canonical_json_bytes(value):
        raise VerificationError(f"JSON is not canonical: {path}")
    return value


def run_git(root, *args, check=True):
    result = subprocess.run(["git", *args], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if check and result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip().replace("\n", " | ")
        raise VerificationError(f"git command failed: {' '.join(args)}: {detail}")
    return result


def git_text(root, *args):
    return run_git(root, *args).stdout.decode("utf-8").strip()


def reject_unstable(value, label="evidence"):
    if isinstance(value, float):
        raise VerificationError(f"floating-point value is not allowed: {label}")
    if isinstance(value, dict):
        for key, item in value.items():
            if key in UNSTABLE_KEYS:
                raise VerificationError(f"unstable host field is not allowed: {label}.{key}")
            reject_unstable(item, f"{label}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            reject_unstable(item, f"{label}[{index}]")
    elif isinstance(value, str):
        if ABSOLUTE_PATH.match(value) or TIMESTAMP.match(value):
            raise VerificationError(f"absolute path or timestamp is not allowed: {label}")


def expected_components(root):
    lock = load_json(Path(root) / "manifests/components.lock.json")
    components = lock.get("components")
    if not isinstance(components, list) or {item.get("name") for item in components} != {"fdkernel", "freecom", "country"}:
        raise VerificationError("component lock is incomplete")
    return sorted(components, key=lambda item: item["name"])


def verify_baseline(root):
    root = Path(root).resolve()
    if root.name != "freedos-pc88va":
        raise VerificationError(f"repository basename is not freedos-pc88va: {root.name}")
    actual_root = Path(git_text(root, "rev-parse", "--show-toplevel")).resolve()
    if actual_root != root:
        raise VerificationError(f"repository root mismatch: {actual_root}")
    head = git_text(root, "rev-parse", "HEAD")
    if run_git(root, "merge-base", "--is-ancestor", BASELINE_PARENT_COMMIT, head, check=False).returncode != 0:
        raise VerificationError("parent baseline is not the accepted M02R1 commit ancestry")
    origin = git_text(root, "remote", "get-url", "origin")
    if origin not in {PARENT_REPOSITORY, PARENT_REPOSITORY.removesuffix(".git") }:
        raise VerificationError(f"parent origin mismatch: {origin!r}")

    expected_digests = {
        "manifests/components.lock.json": M01_COMPONENTS_LOCK_SHA256,
        "manifests/toolchains.lock.json": M01_TOOLCHAIN_LOCK_SHA256,
        "manifests/m01-build-contract.json": M01_BUILD_CONTRACT_SHA256,
        "qa/golden/m01-baseline.json": M01_GOLDEN_SHA256,
        "qa/golden/m02/bundle-manifest.json": M02_GOLDEN_SHA256,
    }
    for relative, expected in expected_digests.items():
        path = root / relative
        if not path.is_file() or sha256_file(path) != expected:
            raise VerificationError(f"accepted baseline digest mismatch: {relative}")
    m02 = load_canonical(root / "qa/golden/m02/bundle-manifest.json")
    archive = m02.get("archive", {})
    if archive.get("size") != M02_TAR_SIZE or archive.get("sha256") != M02_TAR_SHA256 or archive.get("sidecar_sha256") != M02_SIDECAR_SHA256:
        raise VerificationError("accepted M02 archive identity is not preserved")

    components = expected_components(root)
    expected_links = {item["path"]: item["commit"] for item in components}
    for component in components:
        component_root = root / component["path"]
        actual = git_text(component_root, "rev-parse", "HEAD")
        if actual != component["commit"]:
            raise VerificationError(f"component commit mismatch: {component['path']}")
        if run_git(component_root, "status", "--porcelain=v1", "--untracked-files=all").stdout:
            raise VerificationError(f"component worktree is dirty: {component['path']}")
        stage = git_text(root, "ls-files", "--stage", "--", component["path"]).split()
        if len(stage) < 2 or stage[0] != "160000" or stage[1] != component["commit"]:
            raise VerificationError(f"parent gitlink mismatch: {component['path']}")
        configured_url = git_text(root, "config", "-f", ".gitmodules", f"submodule.{component['path']}.url")
        if configured_url != component.get("repository"):
            raise VerificationError(f"component repository mismatch: {component['path']}")
    link_paths = {path for path in expected_links}
    actual_link_paths = set(git_text(root, "ls-files", "components").splitlines())
    actual_link_paths = {path for path in actual_link_paths if path in link_paths}
    if actual_link_paths != link_paths:
        raise VerificationError("component gitlink path set changed")

    for protected in PROTECTED_PATHS:
        if run_git(root, "diff", "--quiet", BASELINE_PARENT_COMMIT, "--", protected, check=False).returncode != 0:
            raise VerificationError(f"M01/M02 protected evidence or component path changed: {protected}")
    if (root / "components/necpc88va").exists() or (root / "components/pc88va").exists():
        raise VerificationError("a prohibited PC-88VA component tree was created")
    changed = git_text(root, "diff", "--name-only", f"{BASELINE_PARENT_COMMIT}..HEAD").splitlines()
    validate_changed_paths(changed)
    return components


def validate_changed_paths(changed):
    for relative in changed:
        suffix = PurePosixPath(relative).suffix.lower()
        parts = set(PurePosixPath(relative).parts)
        if relative.startswith("qa/results/") or suffix in PRIVATE_OR_BINARY_SUFFIXES or {"private", "rom", "bios"} & parts:
            raise VerificationError(f"generated/private/binary file is committed: {relative}")
        if relative.startswith("components/"):
            raise VerificationError(f"component source or gitlink changed: {relative}")


def validate_document_fact(fact, registered_source_ids):
    if fact.get("classification") != "DOCUMENT_FACT":
        return
    source_id = fact.get("source_id")
    page = fact.get("page_reference")
    if not isinstance(source_id, str) or source_id not in registered_source_ids:
        raise VerificationError("DOCUMENT_FACT has no registered source ID")
    if not isinstance(page, str) or not page or page == "UNKNOWN":
        raise VerificationError("DOCUMENT_FACT has no document/page reference")


def validate_pc88va_support(fact):
    if fact.get("platform") == "pc88va" and fact.get("support_material") in {"nec98", "pc98"}:
        raise VerificationError("PC-88VA fact is supported only by PC-98 material")


def validate_blocker_records(records):
    for record in records:
        if record.get("current_state") == "RESOLVED":
            evidence = record.get("accepted_evidence")
            if not isinstance(evidence, list) or not evidence or any(item in {"UNKNOWN", ""} for item in evidence):
                raise VerificationError(f"resolved blocker has no accepted evidence: {record.get('question_id')}")


def validate_entries(data, components, root=None):
    required = {"schema_version", "scanner", "parent_gitlinks", "components", "surface_coverage", "rules", "entries", "counts", "limitations"}
    if set(data) != required:
        raise VerificationError(f"census top-level schema mismatch: {sorted(set(data) ^ required)}")
    scanner = data["scanner"]
    if scanner != {
        "name": SCANNER_NAME,
        "version": SCANNER_VERSION,
        "ruleset_sha256": ruleset_sha256(),
        "baseline_parent_commit": BASELINE_PARENT_COMMIT,
    }:
        raise VerificationError("scanner identity or ruleset digest is not accepted")
    expected_links = sorted(({"path": item["path"], "commit": item["commit"]} for item in components), key=lambda item: item["path"])
    if data["parent_gitlinks"] != expected_links:
        raise VerificationError("census parent gitlinks do not match the component lock")
    expected_component_records = []
    repository_root = Path(root or Path.cwd())
    for component in components:
        component_root = repository_root / component["path"]
        tracked = subprocess.check_output(["git", "-C", str(component_root), "ls-files"], text=True).splitlines()
        tree = subprocess.check_output(["git", "-C", str(component_root), "rev-parse", "HEAD^{tree}"], text=True).strip()
        expected_component_records.append({
            "name": component["name"],
            "path": component["path"],
            "commit": component["commit"],
            "tree": tree,
            "tracked_file_count": len(tracked),
        })
    expected_component_records.sort(key=lambda item: item["name"])
    if data["components"] != expected_component_records:
        raise VerificationError("census component tree identity mismatch")
    if data["surface_coverage"] != list(SURFACES):
        raise VerificationError("required surface category coverage is incomplete or unsorted")
    if data["rules"] != ruleset_descriptors():
        raise VerificationError("census contains an undocumented or changed scanner rule")
    entries = data["entries"]
    if not isinstance(entries, list) or not entries:
        raise VerificationError("census entries are missing")
    if entries != sorted(entries, key=lambda item: (item.get("component", ""), item.get("path", ""), item.get("matched_rule", ""), item.get("symbol_or_section", ""), item.get("evidence_excerpt_or_token", ""), item.get("id", ""))):
        raise VerificationError("census entries are not deterministically sorted")
    component_by_name = {item["name"]: item for item in components}
    rules_by_id = {item["id"]: item for item in RULES}
    ids = set()
    for entry in entries:
        if set(entry) != set(REQUIRED_ENTRY_FIELDS):
            raise VerificationError("census entry schema mismatch")
        if entry["id"] in ids:
            raise VerificationError(f"duplicate census entry ID: {entry['id']}")
        ids.add(entry["id"])
        if entry["component"] not in component_by_name or entry["component_commit"] != component_by_name[entry["component"]]["commit"]:
            raise VerificationError("census component commit mismatch")
        path = entry["path"]
        safe = PurePosixPath(path)
        if safe.is_absolute() or ".." in safe.parts or not path.startswith(f"components/{entry['component']}/"):
            raise VerificationError(f"unsafe census source path: {path}")
        if entry["platform"] not in PLATFORMS or entry["surface"] not in SURFACES or entry["mechanism"] not in MECHANISMS or entry["disposition"] not in DISPOSITIONS or entry["classification"] not in CLASSIFICATIONS or entry["target_milestone"] not in TARGET_MILESTONES:
            raise VerificationError(f"census closed-vocabulary value is invalid: {entry['id']}")
        if not entry["id"] or not re.fullmatch(r"[0-9a-f]{16}", entry["id"]):
            raise VerificationError("census entry ID is malformed")
        rule_item = rules_by_id.get(entry["matched_rule"])
        if rule_item is None:
            raise VerificationError(f"census rule is undocumented: {entry['matched_rule']}")
        for field in ("surface", "mechanism", "disposition", "target_milestone", "candidate_boundary", "confidence", "notes"):
            if entry[field] != rule_item[field]:
                raise VerificationError(f"census rule metadata mismatch: {entry['id']}.{field}")
        for field in ("path", "symbol_or_section", "evidence_excerpt_or_token", "candidate_boundary", "notes"):
            if not isinstance(entry[field], str) or not entry[field].isascii():
                raise VerificationError(f"census text token is not stable ASCII: {entry['id']}.{field}")
        validate_document_fact(entry, set())
        validate_pc88va_support(entry)
    expected_counts = {
        "component": counts(entries, "component"),
        "surface": counts(entries, "surface"),
        "mechanism": counts(entries, "mechanism"),
        "disposition": counts(entries, "disposition"),
        "target_milestone": counts(entries, "target_milestone"),
    }
    if data["counts"] != expected_counts:
        raise VerificationError("census counts do not match entries")
    reject_unstable(data)
    return data


def validate_census_file(root, path, components):
    data = load_canonical(path)
    return validate_entries(data, components, root)


def comparison_report(first_path, second_path, first, second):
    first_bytes = Path(first_path).read_bytes()
    second_bytes = Path(second_path).read_bytes()
    identical = first_bytes == second_bytes
    return {
        "schema_version": 1,
        "status": "pass" if identical else "fail",
        "byte_identical": identical,
        "run_1": {"path": "run-1/port-surface.json", "size": len(first_bytes), "sha256": sha256_bytes(first_bytes)},
        "run_2": {"path": "run-2/port-surface.json", "size": len(second_bytes), "sha256": sha256_bytes(second_bytes)},
        "entry_count": len(first.get("entries", [])),
    }


def compare(root, run1, run2, output):
    components = verify_baseline(root)
    first = validate_census_file(root, run1, components)
    second = validate_census_file(root, run2, components)
    report = comparison_report(run1, run2, first, second)
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_bytes(canonical_json_bytes(report))
    if not report["byte_identical"]:
        raise VerificationError("M03 run-1/run-2 census output differs")
    print(f"M03 comparison passed: {report['entry_count']} entries and byte-identical census JSON")


def verify(root, run1, run2, golden, sidecar, comparison):
    components = verify_baseline(root)
    run1_data = validate_census_file(root, run1, components)
    run2_data = validate_census_file(root, run2, components)
    comparison_data = load_canonical(comparison)
    if comparison_data.get("status") != "pass" or comparison_data.get("byte_identical") is not True:
        raise VerificationError("M03 comparison evidence is not passing")
    golden_data = validate_census_file(root, golden, components)
    golden_bytes = Path(golden).read_bytes()
    expected_sidecar = f"{sha256_bytes(golden_bytes)}  {Path(golden).name}\n".encode("ascii")
    if Path(sidecar).read_bytes() != expected_sidecar:
        raise VerificationError("M03 golden SHA-256 sidecar is not canonical")
    if run1_data != run2_data or run1_data != golden_data:
        raise VerificationError("M03 census output does not match both the second run and reviewed golden")
    print("M03 verification passed: baseline identity, census schema, deterministic rules, and golden are valid")


def enroll(root, run1, run2, golden, sidecar, comparison, supersede=False):
    components = verify_baseline(root)
    first = validate_census_file(root, run1, components)
    second = validate_census_file(root, run2, components)
    comparison_data = load_canonical(comparison)
    if comparison_data.get("status") != "pass" or comparison_data.get("byte_identical") is not True or first != second:
        raise VerificationError("cannot enroll M03 golden before a passing identical comparison")
    if Path(golden).exists() and not supersede:
        raise VerificationError(f"M03 golden already exists; use explicit supersession only: {golden}")
    Path(golden).parent.mkdir(parents=True, exist_ok=True)
    Path(golden).write_bytes(canonical_json_bytes(first))
    sidecar_text = f"{sha256_file(golden)}  {Path(golden).name}\n"
    Path(sidecar).write_bytes(sidecar_text.encode("ascii"))
    print(f"M03 golden {'superseded and ' if supersede else ''}enrolled explicitly: {golden}")
    print(f"M03 golden SHA-256: {sha256_file(golden)}")


def clean(root):
    result_root = Path(root) / "qa/results/m03"
    if result_root.exists() and not result_root.is_dir():
        raise VerificationError(f"M03 result root is not a directory: {result_root}")
    for relative in ("run-1", "run-2", "comparison.json"):
        path = result_root / relative
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
    result_root.mkdir(parents=True, exist_ok=True)
    print("M03 generated result paths cleaned")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--baseline", action="store_true")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--enroll-golden", action="store_true")
    parser.add_argument("--supersede-golden", action="store_true")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--run1", type=Path, default=Path("qa/results/m03/run-1/port-surface.json"))
    parser.add_argument("--run2", type=Path, default=Path("qa/results/m03/run-2/port-surface.json"))
    parser.add_argument("--golden", type=Path, default=Path("qa/golden/m03/port-surface.json"))
    parser.add_argument("--sidecar", type=Path, default=Path("qa/golden/m03/port-surface.sha256"))
    parser.add_argument("--comparison", type=Path, default=Path("qa/results/m03/comparison.json"))
    args = parser.parse_args()
    operations = [args.baseline, args.compare, args.verify, args.enroll_golden, args.clean]
    if sum(bool(value) for value in operations) != 1:
        parser.error("select exactly one of --baseline, --compare, --verify, --enroll-golden, or --clean")
    root = args.repo_root.resolve()

    def rooted(path):
        return path if path.is_absolute() else root / path

    try:
        if args.baseline:
            verify_baseline(root)
            print("M03 baseline identity passed")
        elif args.clean:
            clean(root)
        elif args.compare:
            compare(root, rooted(args.run1), rooted(args.run2), rooted(args.comparison))
        elif args.enroll_golden:
            if args.supersede_golden is False and rooted(args.golden).exists():
                enroll(root, rooted(args.run1), rooted(args.run2), rooted(args.golden), rooted(args.sidecar), rooted(args.comparison))
            else:
                enroll(root, rooted(args.run1), rooted(args.run2), rooted(args.golden), rooted(args.sidecar), rooted(args.comparison), args.supersede_golden)
        else:
            if args.supersede_golden:
                parser.error("--supersede-golden requires --enroll-golden")
            verify(root, rooted(args.run1), rooted(args.run2), rooted(args.golden), rooted(args.sidecar), rooted(args.comparison))
    except (OSError, VerificationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
