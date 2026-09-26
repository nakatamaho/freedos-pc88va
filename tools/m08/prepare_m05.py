#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Regenerate historical M05 media with the validated current component lock.

M06's orchestration requires its own fixed child. M08 uses the existing M05
descendant validator instead, preserving the M05 specification and builder.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/m05"))
import verify_m05
import build_media
import inspect_media
import compare_media
import common


def main():
    verify_m05.preflight(ROOT)
    common.remove_owned_results(ROOT)
    results = ROOT / "qa/results/m05"
    for name in ("run-1", "run-2"):
        build_media.build_once(ROOT, results / name)
        inspect_media.inspect_run(ROOT, results / name, True)
    comparison = compare_media.compare_runs(results / "run-1", results / "run-2")
    if comparison.get("status") != "pass":
        raise SystemExit("M05 descendant builds differ")
    common.write_canonical_json(results / "comparison.json", comparison)
    subprocess.run([sys.executable, str(ROOT / "tools/m05/verify_m05.py"), "--verify"],
                   cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
