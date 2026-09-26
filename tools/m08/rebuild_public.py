#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Rebuild the synthetic public loader/media from an already clean kernel build.

Run inside the pinned M01 container with exported public sources. Payloads
are checked against accepted public hashes before composition. No private
overlay, firmware or qualification record is opened.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "components/fdkernel/pc88va/tools"))
sys.path.insert(0, str(ROOT / "tools/m08"))
from build_loader import build_stage, read_overlay
from media import compose


def identity(data):
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    golden = json.loads((ROOT / "qa/golden/m08-artifact-manifest.json").read_text())
    epochs = {"KERNEL.SYS": 1787814827, "COMMAND.COM": 1740233872,
              "COUNTRY.SYS": 1779123341}  # Accepted M01 per-component timestamps.
    records = []
    for name, key in (("KERNEL.SYS", "kernel_sys"), ("COMMAND.COM", "extracted_command_com"),
                      ("COUNTRY.SYS", "extracted_country_sys")):
        data = (args.payload_dir / name).read_bytes()
        actual = identity(data)
        assert all(actual[k] == golden["artifacts"][key][k] for k in actual), key
        records.append({"dos_name": name, "data": data, **actual,
                        "source_date_epoch": epochs[name]})
    overlay = read_overlay(ROOT / "config/m08/synthetic-overlay.json")
    assert overlay["layout"]["profile_class"] == "synthetic_rom_free"
    build_stage(overlay, args.output, 2)
    stage2 = (args.output / "stage2.bin").read_bytes()
    def stage1(extent):
        build_stage(overlay, args.output, 1, extent)
        return (args.output / "stage1.bin").read_bytes()
    spec = json.loads((ROOT / "config/m05/media.json").read_text())
    raw, d88, composition = compose(spec, records, stage2, stage1, {510: False, 1022: False})
    artifacts = {"loader_stage1": (args.output / "stage1.bin").read_bytes(),
                 "loader_stage2": stage2, "kernel_sys": records[0]["data"],
                 "raw_media": raw, "d88_media": d88}
    # Independently re-extract final media payloads through the accepted inspector.
    from media import inspect_raw, derive_layout, build_boot_record
    all_records = records + [{"dos_name": "LOADER.BIN", "data": stage2,
                              **identity(stage2), "source_date_epoch": 1787814827}]
    _, extracted = inspect_raw(build_boot_record(spec) + raw[1024:], spec,
                               derive_layout(spec), all_records)
    for name, key in (("KERNEL.SYS", "extracted_kernel_sys"),
                      ("COMMAND.COM", "extracted_command_com"),
                      ("COUNTRY.SYS", "extracted_country_sys")):
        artifacts[key] = extracted[name]
    result = {}
    for name, data in artifacts.items():
        actual = identity(data)
        assert all(actual[k] == golden["artifacts"][name][k] for k in actual), name
        (args.output / (name + ".artifact")).write_bytes(data)
        result[name] = actual
    (args.output / "rebuilt-manifest.json").write_text(
        json.dumps({"artifacts": result, "composition": composition}, sort_keys=True, indent=2) + "\n")
    print("M08 public artifacts rebuilt and matched accepted identities")


if __name__ == "__main__":
    main()
