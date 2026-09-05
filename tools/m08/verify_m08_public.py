#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Verify the public M08 loader contracts without private inputs."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHILD = ROOT / "components/fdkernel/pc88va"


def main():
    contract = json.loads((ROOT / "config/m08/loader-contract.json").read_text())
    if contract["platform"] != "pc88va" or contract["replace_stubs"] != ["pc88va_disk_read", "pc88va_loader_handoff"]:
        raise SystemExit("M08 public loader contract differs")
    if contract["promotion_status"] != "prohibited_pending_user_approval" or contract["hardware_claim"] or contract["dos_runtime_claim"]:
        raise SystemExit("M08 public boundary claims are unsafe")
    required = [CHILD / "boot" / name for name in ("disk_read.inc", "fat12.inc", "root_directory.inc", "file_load.inc", "mz_validate.inc", "mz_transform.inc", "loader_handoff.inc", "stage1.asm", "stage2.asm")]
    if any(not p.is_file() for p in required):
        raise SystemExit("M08 loader source boundary is incomplete")
    print("M08 public parameterized loader contract and source boundary PASS")


if __name__ == "__main__":
    main()
