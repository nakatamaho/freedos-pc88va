#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Check exact predecessor provenance and successful current child CI."""
import argparse
import json
from pathlib import Path
import subprocess

from verify_m14 import ROOT, START, COMPONENTS, check_ci, git, require


def run(repo, number):
    return json.loads(subprocess.check_output([
        "gh", "run", "view", str(number), "--repo", "nakatamaho/" + repo,
        "--json", "headSha,attempt,status,conclusion,jobs"], text=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    remote = "https://github.com/nakatamaho/freedos-pc88va.git"
    branch = "refs/heads/topic/m13-pc88va-readonly-freecom"
    actual = git(ROOT, "ls-remote", remote, branch).decode().split()
    require(actual == [START, branch], "PREDECESSOR_REMOTE_TIP_DRIFT")
    git(ROOT, "fetch", remote, branch)
    require(git(ROOT, "rev-parse", "FETCH_HEAD").decode().strip() == START, "FETCHED_PREDECESSOR_DRIFT")
    subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", START, "HEAD"], check=True)
    historical = run("freedos-pc88va", 35138781354)
    check_ci(historical, "7ddca85c1bf3ee74fea396a27a3a75d91cb78a21",
             ["public-readonly-freecom", "historical-regression"], 1)
    (args.output / "historical-m13-ci.json").write_text(json.dumps(historical, indent=2))
    # The later predecessor had an owner-accepted private checkpoint, not a
    # completed publication gate. Retain its actual failure; do not promote
    # historical success to that different source state.
    predecessor = run("freedos-pc88va", 35515388304)
    require(predecessor["headSha"] == START, "PREDECESSOR_CI_HEAD_DRIFT")
    (args.output / "predecessor-m13-ci.json").write_text(json.dumps(predecessor, indent=2))
    for label, number, jobs in (("build", 35645181467, ["build"]),
                                ("structure", 35645181236, ["structure"])):
        value = run("fdkernel", number)
        check_ci(value, COMPONENTS["fdkernel"], jobs, 1)
        (args.output / ("child-" + label + ".json")).write_text(json.dumps(value, indent=2))
    child_branch = "refs/heads/topic/m14-floppy-write-media-change-published"
    reach = git(ROOT / "components/fdkernel", "ls-remote", "origin", child_branch).decode().split()
    require(reach == [COMPONENTS["fdkernel"], child_branch], "CHILD_NOT_REACHABLE")
    print("M14 predecessor provenance and current child CI verified; private prerequisite is separate")


if __name__ == "__main__":
    main()
