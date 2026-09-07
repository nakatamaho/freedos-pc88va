#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""M13 public evidence and source-boundary verifier."""
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
START = "66138e6539e4220ae7b6d3ffee24581e0d674267"
CHILD = "33da21f248fa7af25f9dd17a7a981c34f8ebec37"
VAEG = "7dd453cbd36014ba453a26765b00cd0cc9a99655"
FREECOM = "855281a3114b43ad4b8d9a320f2aca39be046bba"
COUNTRY = "23f189cca3420606eae8723884fa92ccd65eb307"

class Rejected(RuntimeError):
    pass

def req(ok, msg):
    if not ok:
        raise Rejected(msg)

def load(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise Rejected("INVALID_JSON") from e

def sha(p):
    b = Path(p).read_bytes()
    return len(b), hashlib.sha256(b).hexdigest()

def validate(instance, schema):
    s = load(schema)
    Draft202012Validator.check_schema(s)
    errors = list(Draft202012Validator(s).iter_errors(load(instance)))
    req(not errors, "INVALID_INSTANCE")

def git(path, *args):
    return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()

def ref(value):
    req(isinstance(value, dict) and set(value) == {"path", "sha256"}, "INVALID_REFERENCE")
    req(re.fullmatch(r"[0-9a-f]{64}", value["sha256"]), "INVALID_REFERENCE_HASH")
    p = ROOT / value["path"]
    req(p.is_file() and not p.is_symlink(), "MISSING_REFERENCE")
    req(sha(p)[1] == value["sha256"], "REFERENCE_DIGEST_DRIFT")

def content():
    mc_path = ROOT / "config/m13/machine-contract.json"
    ic_path = ROOT / "config/m13/integration-contract.json"
    validate(mc_path, ROOT / "schema/m13-machine-contract.schema.json")
    validate(ic_path, ROOT / "schema/m13-integration-contract.schema.json")
    mc, ic = load(mc_path), load(ic_path)
    req(mc["start_sha"] == START and mc["child_commit"] == CHILD and mc["freecom_commit"] == FREECOM and mc["country_commit"] == COUNTRY and mc["vaeg_commit"] == VAEG, "IDENTITY_DRIFT")
    req(ic["status"] == mc["status"], "CONTRACT_STATUS_DRIFT")
    for key in ("artifact_manifest", "qualification", "component_lock"):
        ref(mc[key])
    validate(ROOT / "manifests/m13-components.lock.json", ROOT / "schema/m13-components.schema.json")
    lock = load(ROOT / "manifests/m13-components.lock.json")
    expected = {"components/fdkernel": CHILD, "components/freecom": FREECOM, "components/country": COUNTRY}
    for item in lock["components"]:
        p = ROOT / item["path"]
        req(git(p, "rev-parse", "HEAD") == item["commit"], "COMPONENT_HEAD_DRIFT")
        req(not git(p, "status", "--porcelain", "--untracked-files=all"), "DIRTY_COMPONENT")
        req(expected[item["path"]] == item["commit"], "COMPONENT_IDENTITY_DRIFT")
        tree = git(ROOT, "ls-tree", "HEAD", "--", item["path"]).split()
        req(tree[:3] == ["160000", "commit", item["commit"]], "COMPONENT_GITLINK_DRIFT")
    manifest_path = ROOT / "qa/golden/m13/manifest.json"
    validate(manifest_path, ROOT / "schema/m13-artifact-manifest.schema.json")
    manifest = load(manifest_path)
    req(manifest["source"]["child_commit"] == CHILD, "MANIFEST_CHILD_DRIFT")
    for artifact in manifest["artifacts"].values():
        p = ROOT / artifact["path"]
        req(p.is_file(), "MANIFEST_ARTIFACT_MISSING")
        req(sha(p) == (artifact["size"], artifact["sha256"]), "MANIFEST_ARTIFACT_DRIFT")
    qualification_path = ROOT / "qa/golden/m13/qualification.json"
    validate(qualification_path, ROOT / "schema/m13-public-qualification.schema.json")
    qualification = load(qualification_path)
    req(qualification["child_commit"] == CHILD and qualification["vaeg_commit"] == VAEG, "QUALIFICATION_IDENTITY_DRIFT")
    req(qualification["artifact_manifest"]["sha256"] == sha(manifest_path)[1], "QUALIFICATION_MANIFEST_DRIFT")
    req(sha(qualification_path)[1] == mc["qualification"]["sha256"], "MACHINE_QUALIFICATION_BINDING")
    return mc, qualification

def sources():
    child = ROOT / "components/fdkernel"
    plan = load(child / "pc88va/config/m13-build-plan.json")
    common = {x["source"] for x in plan["objects"] if x["classification"] == "common-core"}
    for source in ("kernel/main.c", "kernel/inthndlr.c", "kernel/fatfs.c", "kernel/memmgr.c", "kernel/task.c", "kernel/procsupt.asm"):
        req(source in common, "COMMON_CORE_MISSING")
    text = (child / "pc88va/kernel/m13_platform.asm").read_text(encoding="utf-8")
    for token in ("pc88va_kernel_disk_read_", "reject_word FL_WRITE", "reject_word FL_FORMAT", "mov ax, 5"):
        req(token in text, "ADAPTER_BOUNDARY_MISSING")
    req("pc88va_kernel_disk_read_" in (child / "pc88va/kernel/resident_disk.asm").read_text(encoding="utf-8"), "RESIDENT_READ_MISSING")

def generated(root):
    root = Path(root)
    req((root / "run-1").is_dir() and (root / "run-2").is_dir(), "BUILD_PAIR_MISSING")
    for n in (1, 2):
        req((root / f"run-{n}/build-record.json").is_file(), "BUILD_RECORD_MISSING")
    req((root / "run-1/build-record.json").read_bytes() == (root / "run-2/build-record.json").read_bytes(), "BUILD_PAIR_DRIFT")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-root", type=Path)
    parser.add_argument("--accept", action="store_true")
    args = parser.parse_args()
    try:
        _, qualification = content()
        sources()
        if args.build_root:
            generated(args.build_root)
        if args.accept:
            req(qualification["status"] == "M13 PRIVATE VAEG QUALIFICATION PASS", "PRIVATE_QUALIFICATION_PENDING")
            for key in ("two_main_runs_equal", "two_negative_runs_equal", "actual_schema_instances_valid", "production_memory", "real_freecom", "exec_forms", "readonly_media", "alternate_fixture"):
                req(qualification[key], "QUALIFICATION_GATE_INCOMPLETE")
            subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests/m13", "-p", "test_*.py"], cwd=ROOT, check=True)
        print("M13 public schemas, actual instances, component bindings and common-core source checks passed")
        return 0
    except (Rejected, OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as e:
        print("M13_PUBLIC_GATE_REJECTED: " + (str(e) or "invalid evidence"))
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
