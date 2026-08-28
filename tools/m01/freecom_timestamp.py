#!/usr/bin/env python3
"""Validate and expose the deterministic FreeCOM build timestamp."""

import datetime
import json
import re
import sys
from pathlib import Path


DATE_PATTERN = re.compile(r"[A-Z][a-z]{2} [ 0-9][0-9] [0-9]{4}")
TIME_PATTERN = re.compile(r"[0-9]{2}:[0-9]{2}:[0-9]{2}")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def load_timestamp(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("component") != "freecom" or data.get("timezone") != "UTC":
        raise SystemExit("FreeCOM timestamp metadata has an invalid component or timezone")
    epoch = data.get("source_date_epoch")
    if not isinstance(epoch, int) or epoch < 0:
        raise SystemExit("FreeCOM timestamp epoch is not a non-negative integer")
    date = data.get("formatted_date")
    time = data.get("formatted_time")
    if not isinstance(date, str) or len(date) != 11 or DATE_PATTERN.fullmatch(date) is None:
        raise SystemExit("FreeCOM timestamp date is not a C-compatible 11-byte value")
    if not isinstance(time, str) or len(time) != 8 or TIME_PATTERN.fullmatch(time) is None:
        raise SystemExit("FreeCOM timestamp time is not an 8-byte value")
    instant = datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc)
    expected_date = f"{MONTHS[instant.month - 1]} {instant.day:2d} {instant.year:04d}"
    expected_time = f"{instant.hour:02d}:{instant.minute:02d}:{instant.second:02d}"
    if date != expected_date or time != expected_time:
        raise SystemExit("FreeCOM timestamp metadata does not match its UTC epoch")
    if data.get("date_macro") != "FREECOM_BUILD_DATE" or data.get("time_macro") != "FREECOM_BUILD_TIME":
        raise SystemExit("FreeCOM timestamp macro names are not canonical")
    if data.get("wmake_configuration_variable") != "CFLAGS2":
        raise SystemExit("FreeCOM timestamp configuration variable is not CFLAGS2")
    return epoch, date, time


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: freecom_timestamp.py METADATA_JSON")
    epoch, date, time = load_timestamp(Path(sys.argv[1]))
    print(f"{epoch}\t{date}\t{time}")
