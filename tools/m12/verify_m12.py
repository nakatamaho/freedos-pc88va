#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Fail-closed public M12 verifier; private VAEG evidence stays local."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]
START = "c5ddf7c87cac46d357cfe75d132a819c7cf3fbe4"
CHILD = "d2f2ed4e9070ab42ad15cd1df056e714ed819a86"
VAEG = "7dd453cbd36014ba453a26765b00cd0cc9a99655"
FREECOM = "855281a3114b43ad4b8d9a320f2aca39be046bba"
COUNTRY = "23f189cca3420606eae8723884fa92ccd65eb307"


class Rejected(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise Rejected(message)


def read(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Rejected(f"invalid JSON: {path}") from exc


def digest(path):
    data = path.read_bytes()
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def validate(path, schema_path):
    from jsonschema import Draft202012Validator
    schema = read(schema_path)
    Draft202012Validator.check_schema(schema)
    value = read(path)
    errors = list(Draft202012Validator(schema).iter_errors(value))
    require(not errors, f"schema instance invalid: {path}")
    return value


def git(path, *args):
    return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()


def check_ci(claim):
    require(claim["repository"] == "nakatamaho/fdkernel", "child CI repository drift")
    run = json.loads(subprocess.check_output(["gh", "api", f"repos/{claim['repository']}/actions/runs/{claim['run_id']}"], text=True))
    pages = json.loads(subprocess.check_output(["gh", "api", "--paginate", "--slurp", f"repos/{claim['repository']}/actions/runs/{claim['run_id']}/attempts/{claim['attempt']}/jobs?per_page=100"], text=True))
    require(run.get("head_sha") == claim["head_sha"] and run.get("conclusion") == "success" and run.get("run_attempt") == claim["attempt"], "child CI identity or conclusion drift")
    jobs = {j["name"]: j.get("conclusion") for p in pages for j in p["jobs"]}
    require(all(jobs.get(name) == "success" for name in claim["required_jobs"]), "child required job failure")


def content(root):
    contract = validate(root / "config/m12/floppy-contract.json", root / "schema/m12-floppy-contract.schema.json")
    require(contract["start_sha"] == START and contract["child_commit"] == CHILD and contract["vaeg_commit"] == VAEG, "M12 identity drift")
    machine = validate(root / "config/m12/machine-contract.json", root / "schema/m12-machine-contract.schema.json")
    require(machine["start_sha"] == START and machine["child_commit"] == CHILD and machine["vaeg_commit"] == VAEG, "M12 machine identity drift")
    check_ci(machine["child_ci"])
    lock = validate(root / "manifests/m12-components.lock.json", root / "schema/m12-components.schema.json")
    expected = {"components/fdkernel": CHILD, "components/freecom": FREECOM, "components/country": COUNTRY}
    for item in lock["components"]:
        path = root / item["path"]
        require(git(path, "rev-parse", "HEAD") == item["commit"], "component head drift")
        require(not git(path, "status", "--porcelain", "--untracked-files=all"), "dirty component")
        require(expected[item["path"]] == item["commit"], "component identity drift")
        tree = git(root, "ls-tree", "HEAD", "--", item["path"]).split()
        require(tree[:3] == ["160000", "commit", item["commit"]], "component gitlink drift")
    child = root / "components/fdkernel"
    require(not git(child, "diff", "b08ace36670a05992d8ddaa4279727d9b17bd11e", CHILD, "--", "pc88va/boot"), "M08 loader source changed")
    require((child / "pc88va/kernel/resident_disk.asm").is_file(), "resident service missing")
    require("pc88va_kernel_disk_read_" in (child / "pc88va/kernel/resident_disk.asm").read_text(encoding="utf-8"), "resident entry missing")
    manifest = validate(root / "qa/golden/m12/manifest.json", root / "schema/m12-artifact-manifest.schema.json")
    require(manifest["source"]["commit"] == CHILD, "artifact source drift")
    qualification = validate(root / "qa/golden/m12/qualification.json", root / "schema/m12-public-qualification.schema.json")
    require(qualification["child_commit"] == CHILD and qualification["vaeg_commit"] == VAEG, "qualification identity drift")
    for item in (machine["artifact_manifest"], machine["qualification"], machine["component_lock"]):
        require(digest(root / item["path"])["sha256"] == item["sha256"], "machine contract binding drift")
    require(digest(root / "qa/golden/m12/manifest.json")["sha256"] == qualification["artifact_manifest"]["sha256"], "qualification manifest binding drift")
    return contract, lock, manifest, machine, qualification


def generated(root, build):
    _, _, manifest, _, _ = content(root)
    build = Path(build)
    require((build / "run-1").is_dir() and (build / "run-2").is_dir(), "M12 clean build pair missing")
    for rel in ("media/loader_stage1.artifact", "media/loader_stage2.artifact", "media/kernel_sys.artifact", "media/raw_media.artifact", "media/d88_media.artifact"):
        require(digest(build / "run-1" / rel) == digest(build / "run-2" / rel), "M12 build pair drift")
    mapping = {"loader_stage1": "media/loader_stage1.artifact", "loader_stage2": "media/loader_stage2.artifact", "kernel_sys": "media/kernel_sys.artifact", "raw_media": "media/raw_media.artifact", "d88_media": "media/d88_media.artifact"}
    for name, rel in mapping.items():
        require(digest(build / "run-1" / rel) == {k: manifest["artifacts"][name][k] for k in ("size", "sha256")}, f"M12 manifest drift: {name}")
    fixture = json.loads((build / "run-1/media/m12-fixture.json").read_text(encoding="utf-8"))
    require(fixture == manifest["fixture"], "M12 fixture binding drift")
    for lba, expected in ((200, manifest["fixture"]["sectors"]["200"]), (201, manifest["fixture"]["sectors"]["201"])):
        data = bytes(((lba * 17 + offset * 29 + 3) & 0xff) for offset in range(1024))
        require(digest_bytes(data) == expected, "M12 fixture sector drift")


def digest_bytes(data):
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--build-root", type=Path); ap.add_argument("--accept", action="store_true")
    args = ap.parse_args()
    try:
        _, _, _, machine, qualification = content(ROOT)
        if args.accept:
            require(machine["status"] in ("qualified", "accepted"), "M12 machine contract is not qualified")
            require(qualification["status"] == "M12 PRIVATE VAEG QUALIFICATION PASS", "M12 private qualification is pending")
            require(all(qualification[key] for key in ("two_main_runs_equal", "two_error_runs_equal", "actual_schema_instances_valid", "production_memory_trace")), "M12 private qualification gate incomplete")
            subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests/m12", "-p", "test_*.py"], cwd=ROOT, check=True)
        if args.build_root:
            generated(ROOT, args.build_root.resolve())
        print("M12 public schemas, instances, component locks and resident source checks passed")
        return 0
    except (Rejected, OSError, subprocess.CalledProcessError, ValueError, KeyError, TypeError) as exc:
        print(f"M12_PUBLIC_GATE_REJECTED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
