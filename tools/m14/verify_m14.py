#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Shared public M14 acceptance checks; private execution is a separate gate."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from jsonschema import Draft202012Validator, ValidationError, SchemaError

ROOT = Path(__file__).resolve().parents[2]
START = "e324fa6c7132c7daaa7b936c0902563f47a3e528"
COMPONENTS = {
    "fdkernel": "ac16c8a7401526f99787e03babdb2f4223d48fc4",
    "freecom": "9cf57b28abf1d98fab7655fb811375a2aa16c6d9",
    "country": "23f189cca3420606eae8723884fa92ccd65eb307",
}
GATES = tuple("M14-" + name for name in (
    "BASE", "MEM", "BLOCK", "VERIFY", "REJECT", "PROTECT", "ERROR", "CHANGE",
    "FILES", "FAT", "FULL", "PERSIST", "SHELL", "REGRESS", "NORMAL", "CLOSE"))
PRIVATE_GATES = {
    "M14-BASE": ["control", "editing", "normal-write"],
    "M14-MEM": ["memory", "host"],
    "M14-BLOCK": ["raw-patterns", "raw-restore"],
    "M14-VERIFY": ["raw-patterns", "raw-restore", "host"],
    "M14-REJECT": ["raw-patterns", "host"],
    "M14-PROTECT": ["raw-protect", "raw-missing", "exchange-protect", "exchange-missing"],
    "M14-ERROR": ["raw-partial", "io-control", "io-retry"],
    "M14-CHANGE": ["exchange-clean", "exchange-protect", "exchange-missing",
                   "exchange-recovery", "io-swap", "io-retry"],
    "M14-FILES": ["memory"],
    "M14-FAT": ["data-full", "root-full", "host"],
    "M14-FULL": ["data-full", "root-full"],
    "M14-PERSIST": ["data-reread", "normal-reboot"],
    "M14-SHELL": ["normal-write", "data-reread", "exchange-recovery"],
    "M14-REGRESS": ["host", "control", "editing"],
    "M14-NORMAL": ["normal-write", "normal-reboot"],
}


class Rejected(ValueError):
    """A missing, stale or invalid acceptance dependency."""


def require(ok, reason):
    if not ok:
        raise Rejected(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def validate(instance, schema):
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(instance)


def reference(root, value):
    require(isinstance(value, dict) and set(value) == {"path", "sha256"}, "REFERENCE_FIELDS")
    require(isinstance(value["sha256"], str) and
            re.fullmatch(r"[0-9a-f]{64}", value["sha256"]), "REFERENCE_HASH")
    name = Path(value["path"])
    require(not name.is_absolute() and ".." not in name.parts, "REFERENCE_PATH")
    path = root / name
    require(path.is_file() and not path.is_symlink() and
            path.resolve().is_relative_to(root.resolve()), "REFERENCE_MISSING_OR_ESCAPE")
    require(digest(path.read_bytes()) == value["sha256"], "REFERENCE_DIGEST_DRIFT")
    return path


def check_ci(value, head, required_jobs, attempt):
    require(value.get("headSha") == head and value.get("attempt") == attempt and
            value.get("status") == "completed" and value.get("conclusion") == "success",
            "CI_HEAD_ATTEMPT_OR_CONCLUSION")
    jobs = value.get("jobs", [])
    require(len({x["name"] for x in jobs}) == len(jobs), "CI_DUPLICATE_JOB")
    indexed = {x["name"]: x for x in jobs}
    for name in required_jobs:
        job = indexed.get(name, {})
        require(job.get("status") == "completed" and job.get("conclusion") == "success",
                "CI_REQUIRED_JOB")
        require(bool(job.get("steps")) and all(
            step.get("conclusion") in ("success", "skipped") for step in job["steps"]),
            "CI_JOB_STEPS")


def content(root=ROOT, check_git=True):
    schema = load(root / "schema/m14-acceptance.schema.json")
    documents = {}
    for kind, path in (
        ("components", "manifests/m14-components.lock.json"),
        ("manifest", "qa/golden/m14/manifest.json"),
        ("qualification", "qa/golden/m14/qualification.json"),
        ("contract", "config/m14/machine-contract.json"),
    ):
        value = load(root / path)
        validate(value, schema)
        require(value["kind"] == kind, "DOCUMENT_KIND")
        documents[kind] = value
    lock, manifest, qual, contract = (documents[k] for k in
                                    ("components", "manifest", "qualification", "contract"))
    require(contract["start_sha"] == START, "START_DRIFT")
    require(contract["components"] == COMPONENTS == qual["components"], "SOURCE_IDENTITY_DRIFT")
    require(set(lock["components"]) == set(COMPONENTS), "COMPONENT_TOPOLOGY")
    require(set(qual["gates"]) == set(GATES), "GATE_TOPOLOGY")
    require(contract["status"] == qual["status"], "STATUS_DRIFT")
    expected_refs = {
        "component_lock": "manifests/m14-components.lock.json",
        "artifact_manifest": "qa/golden/m14/manifest.json",
        "qualification": "qa/golden/m14/qualification.json",
        "toolchain": "manifests/toolchains.lock.json",
        "schema": "schema/m14-acceptance.schema.json",
    }
    for key, expected in expected_refs.items():
        require(contract[key]["path"] == expected, "REFERENCE_TOPOLOGY")
        reference(root, contract[key])
    require(qual["artifact_manifest"] == contract["artifact_manifest"], "QUALIFICATION_MANIFEST")
    paths = [item["path"] for item in manifest["artifacts"]]
    require(len(paths) == len(set(paths)), "MANIFEST_DUPLICATE")
    expected = {p.relative_to(root).as_posix() for base in
                ("tools/m14", "tests/m14", "tests/m13", "tools/m13")
                for p in (root / base).rglob("*")
                if p.is_file() and p.suffix in (".py", ".sh", ".asm", ".txt")}
    expected |= {"config/m05/media.json", "config/m08/low-staging-overlay.json",
                 "config/m01/freecom-build-timestamp.json",
                 "docs/porting/m14-write-media-contract.md", "Makefile",
                 "schema/m14-private-qualification.schema.json"}
    expected |= {p.relative_to(root).as_posix() for p in (root / ".github/workflows").glob("*.yml")}
    require(set(paths) == expected, "MANIFEST_INCOMPLETE_OR_UNKNOWN_SOURCE")
    for value in manifest["artifacts"]:
        reference(root, value)
    for name, sha in COMPONENTS.items():
        item = lock["components"][name]
        require(item["commit"] == sha and item["path"] == "components/" + name,
                "COMPONENT_PIN_DRIFT")
        repository = {"fdkernel": "https://github.com/nakatamaho/fdkernel.git",
                      "freecom": "https://github.com/nakatamaho/freecom_dbcs2.git",
                      "country": "https://github.com/FDOS/country.git"}[name]
        upstream = repository.replace("nakatamaho/", "lpproj/") if name != "country" else None
        require(item["repository"] == repository and item["upstream"] == upstream,
                "COMPONENT_PROVENANCE_DRIFT")
        if check_git:
            child = root / item["path"]
            require(git(child, "rev-parse", "HEAD").decode().strip() == sha, "COMPONENT_HEAD_DRIFT")
            require(not git(child, "status", "--porcelain", "--untracked-files=all"), "DIRTY_COMPONENT")
            tree = git(root, "ls-tree", "HEAD", "--", item["path"]).decode().split()
            require(tree[:3] == ["160000", "commit", sha], "COMPONENT_GITLINK_DRIFT")
            archive = git(child, "archive", "--format=tar", "--prefix=" + name + "/", sha)
            require(digest(archive) == item["source_archive_sha256"], "SOURCE_ARCHIVE_DRIFT")
    if check_git:
        subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", START, "HEAD"], check=True)
        # Preserve the existing root license checks without reinterpreting an
        # obsolete milestone's component-pin overlay as the active source pin.
        import importlib.util
        sys.path.insert(0, str(root / "tools/qa"))
        spec = importlib.util.spec_from_file_location("m14_license", root / "tools/qa/verify_license_policy.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.verify_copying(root)
        module.verify_notice(root)
    return documents


def build_pair(root, contract):
    records = [load(root / f"run-{n}/build-record.json") for n in (1, 2)]
    require(records[0] == records[1], "BUILD_PAIR_DRIFT")
    record = records[0]
    require(record["child_commit"] == COMPONENTS["fdkernel"], "BUILD_CHILD_DRIFT")
    require(record["toolchain_sha256"] == contract["toolchain"]["sha256"], "BUILD_TOOLCHAIN_DRIFT")
    require(record["architecture"] == "amd64" and record["uname"] == "x86_64",
            "BUILD_ARCHITECTURE")
    require(record["source_date_epoch"] == 1787814827 and record["upx"] is False,
            "BUILD_SETTINGS")
    lock = load(reference(ROOT, contract["component_lock"]))
    require(record["source_archive_sha256"] == lock["components"]["fdkernel"]["source_archive_sha256"],
            "BUILD_SOURCE_DRIFT")
    require(record["freecom_commit"] == COMPONENTS["freecom"] and
            record["freecom_archive_sha256"] == lock["components"]["freecom"]["source_archive_sha256"] and
            record["freecom_timestamp_sha256"] == digest((ROOT / "config/m01/freecom-build-timestamp.json").read_bytes()),
            "BUILD_FREECOM_DRIFT")
    expected = {"KERNEL.SYS", "COMMAND.COM"} | {"m14_" + n + ".com" for n in ("file", "full", "swap", "io", "read")}
    expected |= {"probe-" + n + ".exe" for n in ("0", "1", "protect", "missing", "partial")}
    require(set(record["artifacts"]) == expected, "BUILD_ARTIFACTS_MISSING_OR_UNKNOWN")
    for name, identity in record["artifacts"].items():
        require(Path(name).name == name, "BUILD_ARTIFACT_PATH")
        for number in (1, 2):
            data = (root / f"run-{number}" / name).read_bytes()
            require(identity == {"size": len(data), "sha256": digest(data)}, "BUILD_ARTIFACT_DRIFT")
    return record


def private_evidence(root, documents):
    """Close identified runtime dependencies without publishing their values."""
    bundle = load(root / "qualification.json")
    validate(bundle, load(ROOT / "schema/m14-private-qualification.schema.json"))
    require(bundle["components"] == COMPONENTS, "PRIVATE_COMPONENT_DRIFT")
    require(bundle["public_manifest_sha256"] == documents["contract"]["artifact_manifest"]["sha256"],
            "PRIVATE_PUBLIC_SOURCE_DRIFT")
    require(bundle["gates"] == PRIVATE_GATES, "PRIVATE_GATE_TOPOLOGY")
    cases = {item["id"]: item for item in bundle["cases"]}
    require(len(cases) == len(bundle["cases"]), "PRIVATE_DUPLICATE_CASE")
    used = {name for names in bundle["gates"].values() for name in names}
    require(used == set(cases), "PRIVATE_CASE_REFERENCES_INCOMPLETE")
    for name, case in cases.items():
        expected_child = ("b4af4c6c55979ae22843f1b1ec33d5512e4fdc38" if name == "control"
                          else COMPONENTS["fdkernel"])
        require(case["child_commit"] == expected_child, "PRIVATE_CASE_SOURCE_DRIFT")
        checked = load(reference(root, case["checked"]))
        require(isinstance(checked, dict) and bool(checked), "PRIVATE_EMPTY_CHECK")
        if case["scope"] != "host-regression":
            process = load(reference(root, case["process"]))
            require(process.get("exit_code") == 0, "PRIVATE_RUN_FAILED")
            launch = load(reference(root, case["launch"]))
            require(isinstance(launch.get("command"), list) and launch["command"], "PRIVATE_LAUNCH_MISSING")
        else:
            require(case["process"] is None and case["launch"] is None, "PRIVATE_HOST_TOPOLOGY")
        require(bool(case["artifacts"]), "PRIVATE_ARTIFACTS_MISSING")
        names = {Path(item["path"]).name for item in case["artifacts"]}
        required = set()
        if case["scope"] != "host-regression":
            required |= {"vaeg.cfg", "fresh-backup.dat", "runtime.log"}
        if case["scope"] in ("ordinary", "frontend-automation"):
            required |= {"media.d88", "tvram.bin"}
        if case["scope"] == "ordinary":
            required.add("input.txt")
        if case["scope"] == "device-exchange":
            required |= {"a.d88", "a-before.d88", "b.d88", "b-before.d88", "run.debug", "tvram.bin", "events.tsv"}
        if case["scope"] == "exclusive-block":
            required |= {"before.d88", "media.d88", "protected.d88", "run.debug", "events.tsv", "complete.registers.tsv", "complete.tvram.bin"}
        if case["scope"] == "frontend-automation":
            required |= {"frontend_keys.dylib", "frontend_keys.c", "keys.txt"}
        require(required <= names, "PRIVATE_CASE_DEPENDENCIES_MISSING")
        for artifact in case["artifacts"]:
            reference(root, artifact)
        checks = {
            "memory": ("largest_block_fill_verify_free", "subsequent_dos_file_operations", "no_leaked_allocations"),
            "editing": ("real_frontend_backspace_edit", "media_unchanged"),
            "normal-write": ("original_entries_payloads_tails_and_allocations_preserved",),
            "normal-reboot": ("fresh_boot_reread", "media_unchanged"),
            "data-reread": ("whole_media_unchanged", "eof_and_close_checked"),
            "data-full": ("filesystem_valid", "fat_copies_equal", "exact_full_data_payload"),
            "root-full": ("filesystem_valid", "fat_copies_equal", "exact_expected_file_set_and_payloads"),
            "raw-patterns": ("metadata_unchanged",),
            "raw-restore": ("metadata_unchanged", "restored"),
            "raw-protect": ("zero_completed_bytes_branch_reached", "media_unchanged_after_restoration", "protected_media_unchanged"),
            "raw-missing": ("zero_completed_bytes_branch_reached", "media_unchanged_after_restoration"),
            "raw-partial": ("next_sector_unchanged", "later_valid_extent_restored", "metadata_unchanged"),
            "exchange-clean": ("b_whole_image_unchanged",),
            "exchange-protect": ("explicit_new_operations_after_reinsertion",),
            "exchange-missing": ("explicit_new_operations_after_reinsertion",),
            "exchange-recovery": ("explicit_new_operations_after_reinsertion",),
            "io-control": ("b_whole_image_unchanged", "unrelated_original_files_and_allocations_preserved"),
            "io-retry": ("b_whole_image_unchanged", "unrelated_original_files_and_allocations_preserved"),
            "io-swap": ("b_whole_image_unchanged", "unrelated_original_files_and_allocations_preserved"),
            "host": ("child_tests_passed", "parent_tests_passed", "historical_tests_passed"),
            "control": ("readonly_sequence_passed", "control_frontend_edit_passed", "media_unchanged"),
        }
        require(all(checked.get(key) is True for key in checks[name]), "PRIVATE_CASE_INCOMPLETE")
    for name, value in bundle["artifacts"].items():
        reference(root, value)
    rom_manifest = load(reference(root, bundle["artifacts"]["rom_manifest"]))
    require(set(rom_manifest) == {"roms"} and bool(rom_manifest["roms"]), "ROM_DEPENDENCIES_MISSING")
    for value in rom_manifest["roms"]:
        reference(root, value)
    for case in cases.values():
        if case["scope"] != "host-regression":
            launch = load(reference(root, case["launch"]))
            require(launch.get("worker_sha256") == bundle["artifacts"]["worker"]["sha256"],
                    "PRIVATE_WORKER_DRIFT")
            for key in ("helper_sha256", "input_sha256", "probe_sha256"):
                if key in launch:
                    require(launch[key] in {item["sha256"] for item in case["artifacts"]},
                            "PRIVATE_LAUNCH_DEPENDENCY_MISSING")
    # Validate image structure and actual packaged bytes, not just digests of
    # a claimed passing report. Raw probes deliberately own unmounted media.
    sys.path.insert(0, str(ROOT / "tools/m14"))
    from inspect_fat12 import inspect
    media_spec = load(ROOT / "config/m05/media.json")
    _, files = inspect(reference(root, bundle["artifacts"]["normal_input"]).read_bytes(), media_spec)
    require(files["KERNEL.SYS"] == reference(root, bundle["artifacts"]["carrier"]).read_bytes(),
            "PACKAGED_KERNEL_DRIFT")
    require(files["COMMAND.COM"] == reference(root, bundle["artifacts"]["command_com"]).read_bytes(),
            "PACKAGED_FREECOM_DRIFT")
    build = load(reference(root, bundle["artifacts"]["build_comparison"]))
    for key, artifact in (("KERNEL.SYS", "raw_kernel"), ("COMMAND.COM", "command_com")):
        data = reference(root, bundle["artifacts"][artifact]).read_bytes()
        require(build["artifacts"][key] == {"size": len(data), "sha256": digest(data)}, "PRIVATE_BUILD_DRIFT")
    for case in cases.values():
        if case["scope"] != "exclusive-block":
            for artifact in case["artifacts"]:
                if artifact["path"].endswith(".d88"):
                    data = reference(root, artifact).read_bytes()
                    protected = case["id"] == "exchange-protect" and Path(artifact["path"]).name in ("b.d88", "b-before.d88")
                    require(len(data) > 26 and data[26] == (0x10 if protected else 0), "MEDIA_PROTECTION_DRIFT")
                    # The historical fixture parser accepts only writable
                    # containers. After checking the intentional protection
                    # flag, inspect an in-memory writable view of that FAT.
                    view = data[:26] + b"\0" + data[27:] if protected else data
                    inspect(view, media_spec)
    require(cases["normal-write"]["scope"] == "ordinary" and
            cases["normal-reboot"]["scope"] == "ordinary", "NORMAL_DIAGNOSTIC_DEPENDENCY")
    for name in ("normal-write", "normal-reboot"):
        launch = load(reference(root, cases[name]["launch"]))
        require(not {"--debug-script", "--debugger"}.intersection(launch["command"]),
                "NORMAL_DEBUG_DEPENDENCY")
    require(reference(root, bundle["artifacts"]["normal_saved"]).read_bytes() ==
            reference(root, bundle["artifacts"]["normal_reboot_saved"]).read_bytes(),
            "PERSISTED_IMAGE_DRIFT")
    return bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-root", type=Path)
    parser.add_argument("--accept", action="store_true")
    parser.add_argument("--test-image", help="Run the same test suites in this Linux/amd64 image")
    parser.add_argument("--wheelhouse", type=Path)
    parser.add_argument("--test-output", type=Path)
    parser.add_argument("--private-root", type=Path,
                        help="Optional local qualification bundle; never supplied to public CI")
    args = parser.parse_args()
    try:
        documents = content()
        if args.build_root:
            build_pair(args.build_root, documents["contract"])
        if args.private_root:
            private_evidence(args.private_root, documents)
        if args.accept:
            require(args.build_root is not None, "BUILD_PAIR_REQUIRED")
            if args.test_image:
                require(args.wheelhouse is not None and args.test_output is not None, "TEST_INPUTS_REQUIRED")
                command = [sys.executable, "-B", "tools/m14/container_tests.py", "--image", args.test_image,
                           "--wheelhouse", str(args.wheelhouse), "--output", str(args.test_output)]
            else:
                command = [sys.executable, "-B", "tools/m14/run_tests.py"]
            subprocess.run(command, cwd=ROOT, check=True)
            subprocess.run([sys.executable, "-B", "tools/m10/privacy_guard.py", "--start",
                            "14d4b66ab83ce3b3fbe8f543756c7f0b98bc9f35"], cwd=ROOT, check=True)
        print("M14 public source/schema/build checks passed; private VAEG and hardware gates are separate")
        return 0
    except (OSError, ValueError, KeyError, TypeError, ValidationError, SchemaError,
            subprocess.CalledProcessError) as exc:
        print("M14_REJECTED: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
