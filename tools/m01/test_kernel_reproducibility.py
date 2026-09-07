#!/usr/bin/env python3
"""Run the M01R1 deterministic kernel and generated-input regression gate."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


DATE_PATTERN = re.compile(r"[A-Z][a-z]{2} [ 0-9][0-9] [0-9]{4}")


def load(path):
    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def digest(path):
    data = Path(path).read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data)


def fail(message):
    raise SystemExit("error: " + message)


def record_map(records):
    result = {}
    for record in records:
        path = record.get("path")
        if not isinstance(path, str) or path in result:
            fail("diagnostic manifest contains a duplicate or invalid path")
        result[path] = record
    return result


def compare_identity(first, second, label):
    first_map = record_map(first)
    second_map = record_map(second)
    if set(first_map) != set(second_map):
        fail(f"{label} path set differs between run-1 and run-2")
    for path in sorted(first_map):
        left = first_map[path]
        right = second_map[path]
        for field in ("size", "sha256"):
            if left.get(field) != right.get(field):
                fail(f"{label} content differs for {path}: {field}")
    return first_map, second_map


def expected_fdkernel_date(root, contract_path):
    contract = load(contract_path)
    matches = [item for item in contract["components"] if item.get("path") == "components/fdkernel"]
    if len(matches) != 1:
        fail("build contract must contain exactly one fdkernel component")
    epoch = matches[0].get("source_date_epoch")
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 0:
        fail("fdkernel source_date_epoch is invalid")
    output = subprocess.run(
        ["python3", "tools/m01/kernel_timestamp.py", str(contract_path), "components/fdkernel"],
        cwd=root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "TZ": "Asia/Tokyo"},
    )
    if output.returncode != 0:
        fail("fdkernel timestamp helper failed under TZ=Asia/Tokyo")
    fields = output.stdout.rstrip("\n").split("\t")
    if len(fields) != 2 or fields[0] != str(epoch) or DATE_PATTERN.fullmatch(fields[1]) is None:
        fail("fdkernel timestamp helper output is invalid")
    return epoch, fields[1]


def utility_variant_test(root, epoch):
    compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        fail("a C compiler is required for the bin2c deterministic-input regression")
    source = root / "components/fdkernel/sys/bin2c.c"
    with tempfile.TemporaryDirectory(prefix="m01r1-bin2c-") as temporary:
        base = Path(temporary)
        executable = base / "bin2c"
        result = subprocess.run(
            [compiler, "-std=c99", "-Wall", "-Wextra", "-Werror", str(source), "-o", str(executable)],
            cwd=root,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            fail("bin2c deterministic-input regression did not compile: " + result.stderr.strip())
        outputs = []
        for index, timezone in enumerate(("UTC", "Asia/Tokyo")):
            work = base / f"work-{index}"
            work.mkdir()
            input_path = work / "input.bin"
            output_path = work / "output.h"
            input_path.write_bytes(b"m01r1 fixture\0")
            os.utime(input_path, (1700000000 + index * 86400, 1700000000 + index * 86400))
            env = {**os.environ, "SOURCE_DATE_EPOCH": str(epoch), "TZ": timezone}
            result = subprocess.run(
                [str(executable), "input.bin", "output.h", "fixture"],
                cwd=work,
                env=env,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if result.returncode != 0:
                fail("bin2c deterministic-input regression failed: " + result.stderr.decode(errors="replace").strip())
            output_digest, output_size = digest(output_path)
            if output_size == 0 or output_path.stat().st_mtime_ns != epoch * 1_000_000_000:
                fail("bin2c did not set the generated header mtime to SOURCE_DATE_EPOCH")
            outputs.append((output_digest, output_size, output_path.read_bytes()))
        if outputs[0] != outputs[1]:
            fail("bin2c output changed across source mtime, working directory, or timezone variants")
        invalid_work = base / "invalid-epoch"
        invalid_work.mkdir()
        (invalid_work / "input.bin").write_bytes(b"invalid epoch fixture")
        invalid = subprocess.run(
            [str(executable), "input.bin", "output.h", "fixture"],
            cwd=invalid_work,
            env={**os.environ, "SOURCE_DATE_EPOCH": "not-a-decimal-epoch"},
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if invalid.returncode == 0:
            fail("bin2c accepted a malformed SOURCE_DATE_EPOCH")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.repo_root.resolve()
    run1 = root / "qa/results/m01/run-1"
    run2 = root / "qa/results/m01/run-2"
    first_manifest = load(run1 / "manifest.json")
    second_manifest = load(run2 / "manifest.json")
    if first_manifest.get("artifacts") != second_manifest.get("artifacts"):
        fail("complete M01 artifact manifests differ")
    epoch, date = expected_fdkernel_date(root, root / "manifests/m01-build-contract.json")

    first_diagnostic = load(run1 / "diagnostics/object-manifest.json")
    second_diagnostic = load(run2 / "diagnostics/object-manifest.json")
    if first_diagnostic.get("source_date_epoch") != epoch or second_diagnostic.get("source_date_epoch") != epoch:
        fail("diagnostic source_date_epoch does not match the committed contract")
    if first_diagnostic.get("timezone") != "UTC" or second_diagnostic.get("timezone") != "UTC":
        fail("fdkernel diagnostic timezone is not UTC")
    first_objects, second_objects = compare_identity(first_diagnostic["objects"], second_diagnostic["objects"], "object")
    compare_identity(first_diagnostic["source_inputs"], second_diagnostic["source_inputs"], "source input")
    first_generated, second_generated = compare_identity(first_diagnostic["generated_inputs"], second_diagnostic["generated_inputs"], "generated input")
    if first_diagnostic.get("link_response_file") != "kernel/KWC8616.rsp" or second_diagnostic.get("link_response_file") != "kernel/KWC8616.rsp":
        fail("link response file identity is not canonical")
    for field in ("link_response_lines", "link_inputs_in_response_order", "command_lines"):
        if first_diagnostic.get(field) != second_diagnostic.get(field):
            fail(f"{field} differs between isolated runs")
    generated_headers = [path for path in first_generated if path.startswith("sys/b_fat") and path.endswith(".h")]
    if generated_headers != sorted(generated_headers) or len(generated_headers) != 4:
        fail("the four generated FAT headers are not completely recorded")
    for path in generated_headers:
        if first_generated[path].get("mtime_ns") != epoch * 1_000_000_000 or second_generated[path].get("mtime_ns") != epoch * 1_000_000_000:
            fail(f"generated FAT header mtime is not SOURCE_DATE_EPOCH: {path}")

    staged = run1 / "input-staging/fdkernel-nec98.mak"
    if not staged.is_file() or staged.is_symlink():
        fail("staged fdkernel configuration is missing")
    staged_text = staged.read_text(encoding="utf-8")
    encoded_date = date.replace(" ", r"\ ")
    expected_line = f'ALLCFLAGS=-DKERNEL_BUILD_DATE=\\"{encoded_date}\\" '
    if staged_text.count(expected_line) != 1:
        fail("staged fdkernel configuration does not contain the derived deterministic date exactly once")
    version = (root / "components/fdkernel/hdr/version.h").read_text(encoding="utf-8")
    if version.count("#define KERNEL_BUILD_DATE __DATE__") != 1 or version.count("KERNEL_BUILD_DATE") < 4:
        fail("kernel version source does not use the opt-in deterministic date macro")
    if "[compiled \" KERNEL_BUILD_DATE \"]" not in version:
        fail("kernel version source still compiles the ambient date directly")
    kernel_path = run1 / "artifacts/fdkernel-nec98/nec98/bin/kernel.sys"
    alias_path = run1 / "artifacts/fdkernel-nec98/nec98/bin/KWC8616.sys"
    kernel_data = kernel_path.read_bytes()
    if kernel_data != alias_path.read_bytes():
        fail("kernel.sys and KWC8616.sys are not identical aliases")
    stamp = f"[compiled {date}]".encode("ascii")
    if kernel_data.count(stamp) != 1:
        fail("kernel output does not contain exactly one expected deterministic date stamp")
    if len(first_objects) != 58:
        fail(f"unexpected fdkernel object count: {len(first_objects)}")

    utility_variant_test(root, epoch)
    print(f"M01R1 reproducibility passed: kernel stamp {date}, {len(first_objects)} identical objects, fixed generated-header mtimes, and UTC/path/mtime variants")


if __name__ == "__main__":
    main()
