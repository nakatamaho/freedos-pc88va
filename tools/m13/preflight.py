#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Fail-closed M12 prerequisite check for M13."""
import json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
START = "66138e6539e4220ae7b6d3ffee24581e0d674267"
M12_IMPL = "9b508a80eb3c4d33e1bb683f7963ae350067fd14"
CHILD = "21d9f3450276d42e5fedd1ddb9e80485b888cc07"
FREECOM = "855281a3114b43ad4b8d9a320f2aca39be046bba"
COUNTRY = "23f189cca3420606eae8723884fa92ccd65eb307"

def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()

def show(path):
    return json.loads(subprocess.check_output(["git", "-C", str(ROOT), "show", f"{START}:{path}"], text=True))

def check_run(run_id, head, required):
    data = json.loads(subprocess.check_output(["gh", "run", "view", str(run_id), "--repo", "nakatamaho/freedos-pc88va", "--json", "headSha,conclusion,attempt,jobs"], text=True))
    if data.get("headSha") != head or data.get("conclusion") != "success" or data.get("attempt") != 1:
        raise SystemExit("M13_PREFLIGHT_M12_CI_IDENTITY")
    jobs = {j.get("name"): j.get("conclusion") for j in data.get("jobs", [])}
    if any(jobs.get(name) != "success" for name in required):
        raise SystemExit("M13_PREFLIGHT_M12_REQUIRED_JOB")

def main():
    if subprocess.call(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", START, "HEAD"]) != 0:
        raise SystemExit("M13_PREFLIGHT_START_NOT_ANCESTOR")
    machine = show("config/m12/machine-contract.json")
    if machine.get("status") not in ("qualified", "accepted") or machine.get("qualified_implementation_sha") != M12_IMPL or machine.get("child_commit") != "21d9f3450276d42e5fedd1ddb9e80485b888cc07":
        raise SystemExit("M13_PREFLIGHT_M12_CONTRACT")
    lock = show("manifests/m12-components.lock.json")
    expected = {"components/fdkernel": CHILD, "components/freecom": FREECOM, "components/country": COUNTRY}
    for item in lock["components"]:
        if expected.get(item["path"]) != item["commit"]:
            raise SystemExit("M13_PREFLIGHT_M12_COMPONENT")
    check_run(34068685333, M12_IMPL, ["public-resident-floppy", "historical-regression"])
    check_run(34069044160, START, ["public-resident-floppy", "historical-regression"])
    print("M13 M12 prerequisite passed: exact publication, schemas, components and CI verified")

if __name__ == "__main__":
    main()
