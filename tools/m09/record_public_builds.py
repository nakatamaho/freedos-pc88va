#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Record a public golden only after independent build outputs agree."""
import argparse
import hashlib
import json
from pathlib import Path
from compare_maps import compare


def identity(path):
    data = path.read_bytes()
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def record(root):
    first, second = root / "run-1", root / "run-2"
    paths = {p.relative_to(first) for p in first.rglob("*") if p.is_file()}
    if paths != {p.relative_to(second) for p in second.rglob("*") if p.is_file()}:
        raise ValueError("build output membership differs")
    for relative in paths:
        a, b = first / relative, second / relative
        if a.is_symlink() or b.is_symlink():
            raise ValueError("symlink build output rejected")
        if relative.as_posix() == "objects/KVA8616.map":
            compare(a.read_text(), b.read_text())
        elif a.read_bytes() != b.read_bytes():
            raise ValueError("independent build outputs differ")
    compile_record = json.loads((first / "kernel-evidence/compile-manifest.json").read_text())
    source = {"commit": compile_record["component_commit"],
              "archive_sha256": compile_record["source_archive_sha256"]}
    if identity(root / "kernel.tar")["sha256"] != source["archive_sha256"]:
        raise ValueError("source archive does not match collector")
    names = ("loader_stage1", "loader_stage2", "kernel_sys", "raw_media", "d88_media",
             "extracted_kernel_sys", "extracted_command_com", "extracted_country_sys")
    artifacts = {name: identity(first / "media" / (name + ".artifact")) for name in names}
    artifacts["kernel_sys"].update(format="dos-mz", **{
        key: identity(first / "kernel-evidence" / filename)["sha256"]
        for key, filename in (("compile_manifest_sha256", "compile-manifest.json"),
                              ("kernel_interface_sha256", "kernel-interface.json"),
                              ("symbol_evidence_sha256", "symbol-evidence.json"))})
    return {"schema_version": 1, "source": source, "artifacts": artifacts,
            "composition_manifest": identity(first / "media/rebuilt-manifest.json"),
            "two_clean_builds_equal": True, "raw_map_byte_identity_claimed": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = record(args.build_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        stream.write(json.dumps(result, sort_keys=True, indent=2) + "\n")
