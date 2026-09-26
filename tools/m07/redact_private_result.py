#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Redact an M07 local result to the strict public status contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from m07 import M07Error, canonical_bytes, redact_private_result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        private = json.loads(args.input.read_text(encoding="utf-8"))
        public = redact_private_result(private)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(canonical_bytes(public))
    except (OSError, json.JSONDecodeError, M07Error) as exc:
        print(f"M07 REDACTION ERROR: {exc}", file=sys.stderr)
        return 1
    print("M07 private result redacted without publishing private values")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
