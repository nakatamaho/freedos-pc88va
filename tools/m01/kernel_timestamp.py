#!/usr/bin/env python3
"""Derive the M01 fdkernel C build date from its committed UTC epoch."""

import datetime
import json
import re
import sys
from pathlib import Path


MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
DATE_PATTERN = re.compile(r"[A-Z][a-z]{2} [ 0-9][0-9] [0-9]{4}")


def load_timestamp(contract_path, component_path):
    contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    matches = [item for item in contract["components"] if item.get("path") == component_path]
    if len(matches) != 1:
        raise ValueError("build contract must contain exactly one fdkernel component")
    epoch = matches[0].get("source_date_epoch")
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 0:
        raise ValueError("fdkernel source_date_epoch must be a non-negative integer")
    instant = datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc)
    date = f"{MONTHS[instant.month - 1]} {instant.day:2d} {instant.year:04d}"
    if len(date) != 11 or DATE_PATTERN.fullmatch(date) is None:
        raise ValueError("fdkernel build date is not a C-compatible 11-byte value")
    return epoch, date


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: kernel_timestamp.py CONTRACT COMPONENT_PATH")
    try:
        epoch, date = load_timestamp(sys.argv[1], sys.argv[2])
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise SystemExit(f"error: {exc}")
    print(f"{epoch}\t{date}")


if __name__ == "__main__":
    main()
