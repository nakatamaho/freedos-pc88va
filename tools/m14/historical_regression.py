#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Keep read-only negative tests bound to immutable accepted source states."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BASELINES = {"m13": "7ddca85c1bf3ee74fea396a27a3a75d91cb78a21",
             "m12": "66138e6539e4220ae7b6d3ffee24581e0d674267"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    results = []
    for name, sha in BASELINES.items():
        baseline = output / name
        subprocess.run(["git", "-C", str(ROOT), "worktree", "add", "--detach", str(baseline), sha], check=True)
        command = ["git", "-c", "protocol.file.allow=always", "-C", str(baseline)]
        for component in ("fdkernel", "freecom", "country"):
            command.extend(["-c", "submodule.components/" + component + ".url=" +
                            str(ROOT / "components" / component)])
        subprocess.run(command + ["submodule", "update", "--init", "--recursive"], check=True)
        suites = [("tests/m12", "test_*.py")] if name == "m12" else [
            ("tests", "test_m08_*.py"), *[("tests/" + n, "test_*.py") for n in ("m09", "m10", "m11", "m13")]]
        for index, (directory, pattern) in enumerate(suites):
            command = [sys.executable, "-B", "-m", "unittest", "discover", "-s", directory, "-p", pattern]
            with (output / f"{name}-{index}.log").open("xb") as log:
                code = subprocess.run(command, cwd=baseline, stdout=log, stderr=subprocess.STDOUT).returncode
            results.append({"baseline": sha, "suite": directory, "exit_code": code})
        subprocess.run(["git", "-C", str(baseline), "diff", "--exit-code"], check=True)
    (output / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    return 0 if all(item["exit_code"] == 0 for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
