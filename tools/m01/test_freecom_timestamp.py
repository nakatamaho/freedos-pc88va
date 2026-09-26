#!/usr/bin/env python3
"""Test the deterministic FreeCOM timestamp contract without network access."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
METADATA = ROOT / "config/m01/freecom-build-timestamp.json"
VALIDATOR = ROOT / "tools/m01/freecom_timestamp.py"


def run_metadata(path):
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(path)],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def main():
    valid = run_metadata(METADATA)
    assert valid.returncode == 0, valid.stderr
    assert valid.stdout == "1740233872\tFeb 22 2025\t14:17:52\n"

    with tempfile.TemporaryDirectory(prefix="m01-freecom-timestamp-") as temporary:
        temporary_path = Path(temporary)
        day_two = temporary_path / "day-two.json"
        data = json.loads(METADATA.read_text(encoding="utf-8"))
        data.update({"source_date_epoch": 1738458000, "formatted_date": "Feb  2 2025", "formatted_time": "01:00:00"})
        day_two.write_text(json.dumps(data), encoding="utf-8")
        day_two_result = run_metadata(day_two)
        assert day_two_result.returncode == 0, day_two_result.stderr
        assert day_two_result.stdout == "1738458000\tFeb  2 2025\t01:00:00\n"

        for field in ("source_date_epoch", "formatted_date", "formatted_time"):
            malformed = dict(data)
            malformed.pop(field)
            malformed_path = temporary_path / f"missing-{field}.json"
            malformed_path.write_text(json.dumps(malformed), encoding="utf-8")
            assert run_metadata(malformed_path).returncode != 0

        response = '-DFREECOM_BUILD_DATE="Feb 22 2025" -DFREECOM_BUILD_TIME="14:17:52"\n'
        assert response.count('FREECOM_BUILD_DATE="Feb 22 2025"') == 1
        assert len("Feb 22 2025") == 11
        assert len("14:17:52") == 8
        first = valid.stdout
        second = run_metadata(METADATA).stdout
        assert first == second

    source = (ROOT / "components/freecom/shell/ver.c").read_text(encoding="utf-8")
    assert "#ifndef FREECOM_BUILD_DATE" in source
    assert "#ifndef FREECOM_BUILD_TIME" in source
    assert "static const char shelldate[] = FREECOM_BUILD_DATE \" \" FREECOM_BUILD_TIME;" in source
    assert '" [" FREECOM_BUILD_DATE "]' in source

    contract = json.loads((ROOT / "manifests/m01-build-contract.json").read_text(encoding="utf-8"))
    freecom = next(item for item in contract["components"] if item["path"] == "components/freecom")
    assert freecom["timestamp_contract"] == "config/m01/freecom-build-timestamp.json"
    assert freecom["build_commands"] == [["./build.sh", "-r", "dbcs", "nec98", "watcom", "japanese"]]
    compare = (ROOT / "tools/m01/compare_runs.py").read_text(encoding="utf-8")
    assert "byte-mismatch" in compare
    assert "normal" not in compare.lower()
    print("FreeCOM timestamp regression passed: UTC formatting, fallback macros, fixed response values, and raw comparison")


if __name__ == "__main__":
    main()
