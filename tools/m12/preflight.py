#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Revalidate the exact M11 publication before any M12 mutation is accepted."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
START = "c5ddf7c87cac46d357cfe75d132a819c7cf3fbe4"
BRANCH = "topic/m11-pc88va-console-input"
M11_CHILD = "b08ace36670a05992d8ddaa4279727d9b17bd11e"
M11_QUAL = "c574a54d21bead23deeb907b03e3086a06565bcf"
M11_FINAL_CI = 34043805735
JOBS = ["public-console-input", "historical-regression"]


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def show(path):
    return json.loads(subprocess.check_output(["git", "-C", str(ROOT), "show", f"{START}:{path}"], text=True))


def main():
    # fetch-depth=0 checkout provides the named remote ref; avoid a second
    # credentialed network round-trip from CI while still checking the exact
    # fetched remote tip.
    remote_ref = f"refs/remotes/origin/{BRANCH}"
    if git("rev-parse", remote_ref) != START:
        raise SystemExit("M12_PREFLIGHT_M11_REMOTE_TIP_MISMATCH")
    # The exact M11 acceptance records are read from the verified publication,
    # not from mutable M12 files.
    machine = show("config/m11/machine-contract.json")
    if machine["status"] != "accepted" or machine["child_commit"] != M11_CHILD or machine["qualified_implementation_sha"] != M11_QUAL:
        raise SystemExit("M12_PREFLIGHT_M11_CONTRACT_DRIFT")
    qual = show("qa/golden/m11/qualification.json")
    if qual["child_commit"] != M11_CHILD or not qual["actual_schema_instances_valid"]:
        raise SystemExit("M12_PREFLIGHT_M11_QUALIFICATION_DRIFT")
    run = json.loads(subprocess.check_output(["gh", "run", "view", str(M11_FINAL_CI), "--repo", "nakatamaho/freedos-pc88va", "--json", "headSha,conclusion,attempt,jobs"], text=True))
    if run.get("headSha") != START or run.get("conclusion") != "success" or run.get("attempt") != 1:
        raise SystemExit("M12_PREFLIGHT_M11_FINAL_CI_DRIFT")
    names = {j["name"]: j.get("conclusion") for j in run.get("jobs", [])}
    if any(names.get(job) != "success" for job in JOBS):
        raise SystemExit("M12_PREFLIGHT_M11_REQUIRED_JOB_FAILURE")
    if subprocess.call(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", START, "HEAD"]) != 0:
        raise SystemExit("M12_PREFLIGHT_START_NOT_ANCESTOR")
    print("M12 M11 prerequisite passed: exact publication tip, acceptance records and final CI verified")


if __name__ == "__main__":
    main()
