#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Compose M09 public media using the unchanged M08 loader/M05 inspector."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "components/fdkernel/pc88va/tools"), str(ROOT / "tools/m08")]
from build_loader import build_stage, read_overlay
from media import compose, inspect_raw, derive_layout, build_boot_record


def identity(data):
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    accepted = json.loads((ROOT / "qa/golden/m08-artifact-manifest.json").read_text())["artifacts"]
    epochs = {"KERNEL.SYS": 1787814827, "COMMAND.COM": 1740233872, "COUNTRY.SYS": 1779123341}
    records = []
    for name, key in (("KERNEL.SYS", "kernel_sys"), ("COMMAND.COM", "extracted_command_com"),
                      ("COUNTRY.SYS", "extracted_country_sys")):
        data = (args.payload_dir / name).read_bytes()
        actual = identity(data)
        if name != "KERNEL.SYS" and any(actual[k] != accepted[key][k] for k in actual):
            raise ValueError("unchanged payload identity mismatch")
        records.append({"dos_name": name, "data": data, **actual, "source_date_epoch": epochs[name]})
    overlay = read_overlay(ROOT / "config/m08/synthetic-overlay.json")
    if overlay["layout"]["profile_class"] != "synthetic_rom_free":
        raise ValueError("public build requires synthetic overlay")
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
        if name in ("loader_stage1", "loader_stage2"):
            if any(actual[k] != accepted[name][k] for k in actual):
                raise ValueError("accepted M08 loader artifact changed")
        (args.output / (name + ".artifact")).write_bytes(data)
        result[name] = actual
    (args.output / "rebuilt-manifest.json").write_text(
        json.dumps({"artifacts": result, "composition": composition}, sort_keys=True, indent=2) + "\n")
    print("M09 public media composed; M08 loader and unchanged payload identities verified")


if __name__ == "__main__":
    main()
