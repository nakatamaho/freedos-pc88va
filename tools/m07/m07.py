#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Build and verify the deterministic public M07 boot-acceptance probes."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = Path("config/m07/variants.json")
PUBLIC_SCHEMA = Path("schema/m07-public-result.schema.json")
PRIVATE_SCHEMA = Path("schema/m07-private-overlay.schema.json")
PUBLIC_RESULT = Path("config/m07/public-result.json")
GOLDEN = Path("qa/golden/m07-probe-manifest.json")
RESULTS = Path("qa/results/m07")
START_COMMIT = "655d716099d94e94d63f15a9f1c63d85f04f27ec"
IMAGE_TAG = "freedos-pc88va-m01:local"
PROBE_ENTRY = 62
PROBE_BYTES = bytes.fromhex("9087db87c987d2ebfe")
FIRST_MARKER = bytes.fromhex("9087db87c987d2")
JUMP_BYTES = bytes.fromhex("eb3c90")
SIGNATURE = bytes.fromhex("55aa")
EXPECTED_NASM = {
    "size": 1739504,
    "sha256": "ffcfd989c0879f868c6b654d554e0c497c8946061ef3972df16de0c2a3b9f838",
}
EXPECTED_GITLINKS = {
    "components/fdkernel": "69ccdd8699895722fc537d647ec490685532bdc4",
    "components/freecom": "855281a3114b43ad4b8d9a320f2aca39be046bba",
    "components/country": "23f189cca3420606eae8723884fa92ccd65eb307",
}
EXPECTED_IDENTITIES = {
    "m06_component_lock": ("manifests/m06-components.lock.json", "58a900d0ad838f3eacfd8c2f32835634dd96cccc19649a276dc8dee6d5622bc8"),
    "toolchain_lock": ("manifests/toolchains.lock.json", "39c5b3052d71463235a26e8704ab54c1fedb51ee75bb4efb55e6229391a95162"),
    "m01_contract": ("manifests/m01-build-contract.json", "7d66be32b508395d8c36a902389f368e9f38d9abab08085bda89e3d2c5d6d578"),
    "m01_golden": ("qa/golden/m01-baseline.json", "6fcfe834f90ffc602589ddc63b50d90eba33bbc1802b6bff3c9ef6b9d397c7c3"),
    "m02_golden": ("qa/golden/m02/bundle-manifest.json", "4d4e92f92911130109b5b140b2202fc1dfc3abb9af3cd7501b685894d0cb78fd"),
    "m03_golden": ("qa/golden/m03/port-surface.json", "d871c7f188313218c2c9481ea9fe7c6abf6acd6369f996b2641021ad27c80550"),
    "m04_contract": ("config/contracts/m04-provisional-pc88va-boot-media.json", "f2e4efdc9d9e3a31dc100b81896427beeaeaca29d36d692b5dfeb5fb459460f4"),
    "m04_schema": ("config/contracts/m04-provisional-pc88va-boot-media.schema.json", "f50c099211e2e70f959fb1cc70e93553699f9862113b50c7cda7f29816e6b7c0"),
    "m04_evidence": ("config/contracts/m04-evidence-matrix.json", "0612699d305738f2db131cb87c5fa7e9393b206672d6bec27483a602e7e91770"),
    "m05_specification": ("config/m05/media.json", "f8ba0e41300ee6e11d7a1f0cf646e335a09df243afc8e1235efade3d17cd06bc"),
    "m05_schema": ("config/m05/media.schema.json", "0380d30bec213ade393390498510176fcb14a4f904dd6a9c9c22cee50646fd0f"),
    "m05_golden": ("qa/golden/m05-media-manifest.json", "b81c7bfdde36df76edfd9e802c22d90c865329f206c7bbb9dae2ddbe39e4abaa"),
    "m06_contract": ("config/m06/kernel-build.json", "77bc415336ead1a6e7734ca35b49ef235744745c1f60fd482f376fec90c3fdf3"),
    "m06_schema": ("schema/m06-kernel-interface.schema.json", "cce4891a304ba372fc61e48d5809da939b0341d2fc1bf832e03d544f12d8212f"),
    "m06_golden": ("qa/golden/m06-kernel-manifest.json", "db4160329758e5c055bd9c36a5e892903fcd92548a0d5e9feb790f1b51fd47c8"),
    "copying": ("COPYING", "0f1e68d9b4a580cdcca4c5f4e3b8046f7a8759da05edd109cff081bc484b3c4b"),
}
EXPECTED_BASE_RAW = {"size": 1310720, "sha256": "333f1a7fd1385ba347e64ae7511f2ed060b057f3b73e1cec94e0532bc9916f66"}
EXPECTED_BASE_D88 = {"size": 1331888, "sha256": "141959c7fe8ddbaf2d37e9c3078404380cbb27198bfe650a17e6f0aa37c92004"}
EXPECTED_KERNEL = {"size": 4414, "sha256": "d7c864d29bf772b0bb167ac9b0a2c77d391d6c5a32102ba005f0043d981885a2"}
QUESTION_FIELDS = (
    "firmware_attempts_m05_geometry",
    "accepted_signature_profile",
    "initial_sector_reads",
    "initial_load_extent",
    "physical_load_address",
    "entry_cs_ip",
    "initial_register_state",
    "boot_drive_identity",
)
FORBIDDEN_SUFFIXES = {".rom", ".bin", ".img", ".d88", ".log", ".obj", ".o", ".exe", ".sys", ".map"}


class M07Error(RuntimeError):
    """Raised when a public M07 invariant fails."""


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise M07Error(f"cannot parse JSON {path}: {exc}") from exc
    if canonical_bytes(value) != path.read_bytes():
        raise M07Error(f"JSON is not canonical: {path}")
    return value


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identity(path: Path) -> dict[str, object]:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise M07Error(f"unsafe or missing regular file: {path}")
    data = path.read_bytes()
    return {"size": len(data), "sha256": sha256_bytes(data)}


def run(args: list[str], *, cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=cwd, check=False, capture_output=True, text=True)
    if check and result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise M07Error(f"command failed ({' '.join(args)}): {detail}")
    return result


def git(*args: str, cwd: Path = ROOT, check: bool = True) -> str:
    return run(["git", *args], cwd=cwd, check=check).stdout


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise M07Error(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def m05_modules():
    common = load_module("m07_m05_common", ROOT / "tools/m05/common.py")
    sys.modules["common"] = common
    sys.path.insert(0, str(ROOT / "tools/m05"))
    try:
        builder = load_module("m07_m05_builder", ROOT / "tools/m05/build_media.py")
        inspector = load_module("m07_m05_inspector", ROOT / "tools/m05/inspect_media.py")
    finally:
        sys.path.pop(0)
    historical = dict(common.EXPECTED_GITLINKS)
    common.EXPECTED_GITLINKS = {Path(path).name: commit for path, commit in EXPECTED_GITLINKS.items()}

    def validate_historical(component_gitlinks: dict) -> None:
        if component_gitlinks != historical:
            raise common.ValidationError("historical M05 component identities changed")

    common.validate_component_contract = validate_historical
    return common, builder, inspector


def config() -> dict:
    value = load_json(ROOT / CONFIG)
    if value.get("schema_version") != 1 or value.get("parent_commit") != START_COMMIT:
        raise M07Error("M07 configuration identity is invalid")
    if value.get("probe", {}).get("entry_offset") != PROBE_ENTRY:
        raise M07Error("M07 probe entry offset differs")
    variants = value.get("variants")
    expected = [
        ("V00", False, False, False),
        ("V01", True, False, False),
        ("V02", True, True, False),
        ("V03", True, False, True),
        ("V04", True, True, True),
    ]
    observed = [(item.get("id"), item.get("probe"), item.get("signature_510"), item.get("signature_1022")) for item in variants or []]
    if observed != expected:
        raise M07Error("M07 controlled variant matrix differs")
    return value


def gitlink(path: str) -> str:
    fields = git("ls-files", "--stage", "--", path).strip().split()
    if len(fields) < 4 or fields[0] != "160000":
        raise M07Error(f"not a gitlink: {path}")
    return fields[1]


def validate_components(expected: dict[str, str] | None = None) -> None:
    expected = EXPECTED_GITLINKS if expected is None else expected
    for path, commit in expected.items():
        if gitlink(path) != commit:
            raise M07Error(f"component gitlink drift: {path}")
        component = ROOT / path
        if git("rev-parse", "HEAD", cwd=component).strip() != commit:
            raise M07Error(f"component checkout drift: {path}")
        if git("status", "--short", "--untracked-files=all", cwd=component):
            raise M07Error(f"component worktree is dirty: {path}")


def validate_kernel_role(observed: dict[str, object]) -> None:
    if observed != EXPECTED_KERNEL:
        raise M07Error("M06 compile-only carrier identity differs")


def validate_staged_paths(paths: list[str], *, forbid_components: bool = True) -> None:
    for relative in paths:
        lower = relative.lower()
        suffix = Path(lower).suffix
        if suffix in FORBIDDEN_SUFFIXES or lower.startswith("qa/results/"):
            raise M07Error(f"generated or private artifact is staged: {relative}")
        if "pc88va-private-docs" in lower or "private-analysis" in lower or "private-evidence" in lower:
            raise M07Error(f"private path is staged: {relative}")
        if forbid_components and relative.startswith("components/"):
            raise M07Error(f"component change is staged: {relative}")


def validate_tracked_safety() -> None:
    tracked = [item for item in git("ls-files", "-z").split("\0") if item]
    validate_staged_paths(tracked, forbid_components=False)
    staged = [item for item in git("diff", "--cached", "--name-only", "-z").split("\0") if item]
    validate_staged_paths(staged)


def preflight(require_remote: bool = True) -> dict:
    if ROOT.name != "freedos-pc88va" or Path(git("rev-parse", "--show-toplevel").strip()).resolve() != ROOT:
        raise M07Error("repository root identity mismatch")
    if run(["git", "merge-base", "--is-ancestor", START_COMMIT, "HEAD"], check=False).returncode:
        raise M07Error("accepted M06 commit is not an ancestor of HEAD")
    for _, (relative, digest) in EXPECTED_IDENTITIES.items():
        if identity(ROOT / relative)["sha256"] != digest:
            raise M07Error(f"accepted identity mismatch: {relative}")
    validate_components()
    if require_remote:
        remote = git("ls-remote", "--heads", "origin", "refs/heads/necpc88va", cwd=ROOT / "components/fdkernel").split()
        if len(remote) != 2 or remote[0] != EXPECTED_GITLINKS["components/fdkernel"]:
            raise M07Error("accepted fdkernel branch is not remotely reachable")
    cfg = config()
    load_json(ROOT / PUBLIC_SCHEMA)
    load_json(ROOT / PRIVATE_SCHEMA)
    base_raw = ROOT / "qa/results/m06/run-1/media/pc88va-m06-compile-only.img"
    base_d88 = ROOT / "qa/results/m06/run-1/media/pc88va-m06-compile-only.d88"
    kernel = ROOT / "qa/results/m06/run-1/media/extracted/KERNEL.SYS"
    if identity(base_raw) != EXPECTED_BASE_RAW or identity(base_d88) != EXPECTED_BASE_D88:
        raise M07Error("accepted generated M06 media is missing or differs")
    validate_kernel_role(identity(kernel))
    image = run(["docker", "image", "inspect", IMAGE_TAG, "--format", "{{.Architecture}} {{.Id}}"])
    if not image.stdout.startswith("amd64 sha256:"):
        raise M07Error("accepted Linux/amd64 build image is unavailable")
    validate_tracked_safety()
    return cfg


def validate_probe_layout(entry: int, code: bytes) -> None:
    if entry < 62:
        raise M07Error("probe overlaps the required BPB")
    if entry + len(code) > 1024:
        raise M07Error("probe exceeds the 1024-byte boot record")
    if entry <= 510 < entry + len(code) or entry <= 1022 < entry + len(code):
        raise M07Error("probe code overlaps a signature experiment slot")


def validate_probe_bytes(code: bytes) -> None:
    validate_probe_layout(PROBE_ENTRY, code)
    if len(code) > 1024 - PROBE_ENTRY:
        raise M07Error("probe exceeds available boot-record space")
    lower = code.lower()
    if b"/users/" in lower or b"date" in lower or b"time" in lower or b"\\" in lower:
        raise M07Error("probe contains ambient path or time bytes")
    prohibited = {
        0x9C: "stack", 0x9D: "stack", 0xC2: "return", 0xC3: "return",
        0xCA: "return", 0xCB: "return", 0xCC: "interrupt", 0xCD: "interrupt",
        0xCE: "interrupt", 0xCF: "interrupt", 0xE4: "io", 0xE5: "io",
        0xE6: "io", 0xE7: "io", 0xE8: "call", 0xEC: "io", 0xED: "io",
        0xEE: "io", 0xEF: "io", 0xF4: "hlt",
    }
    for opcode in range(0x50, 0x60):
        prohibited[opcode] = "stack"
    for byte in code:
        if byte in prohibited:
            raise M07Error(f"probe contains prohibited {prohibited[byte]} opcode")
    if code != PROBE_BYTES or not code.startswith(FIRST_MARKER) or not code.endswith(b"\xeb\xfe"):
        raise M07Error("probe marker or bounded self-loop differs")


def build_probe(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    source = ROOT / "tools/m07/probe.asm"
    container = run([
        "docker", "create", "--platform", "linux/amd64", "--network", "none",
        "--workdir", "/work", "--entrypoint", "/bin/sh", IMAGE_TAG,
        "-c", "nasm -f bin -o probe.bin probe.asm",
    ]).stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{64}", container):
        raise M07Error("docker did not return a container identity")
    tool_copy = output / "nasm.tool"
    try:
        run(["docker", "cp", str(source), f"{container}:/work/probe.asm"])
        start = run(["docker", "start", "-a", container], check=False)
        if start.returncode:
            raise M07Error(f"NASM probe build failed: {start.stderr.strip() or start.stdout.strip()}")
        run(["docker", "cp", f"{container}:/work/probe.bin", str(output / "probe.bin")])
        run(["docker", "cp", f"{container}:/usr/bin/nasm", str(tool_copy)])
    finally:
        run(["docker", "rm", "-f", container], check=False)
    code = (output / "probe.bin").read_bytes()
    validate_probe_bytes(code)
    if identity(tool_copy) != EXPECTED_NASM:
        raise M07Error("probe assembler identity differs from accepted M06 NASM")
    tool_copy.unlink()
    manifest = {
        "assembler": EXPECTED_NASM,
        "entry_offset": PROBE_ENTRY,
        "first_marker_hex": FIRST_MARKER.hex(),
        "jump_hex": JUMP_BYTES.hex(),
        "probe": identity(output / "probe.bin"),
        "schema_version": 1,
        "self_loop_hex": "ebfe",
        "source": {"path": "tools/m07/probe.asm", **identity(source)},
    }
    write_json(output / "probe-manifest.json", manifest)
    return manifest


def pattern_byte(offset: int) -> int:
    return ((offset // 64) * 49 + (offset % 64) * 23 + 90) & 0xFF


def make_probe_sector(base: bytes, code: bytes, signature_510: bool, signature_1022: bool) -> bytes:
    if len(base) != 1024:
        raise M07Error("base boot record is not 1024 bytes")
    validate_probe_bytes(code)
    sector = bytearray(base)
    sector[0:3] = JUMP_BYTES
    for offset in range(PROBE_ENTRY, 1024):
        sector[offset] = pattern_byte(offset)
    sector[PROBE_ENTRY:PROBE_ENTRY + len(code)] = code
    if signature_510:
        sector[510:512] = SIGNATURE
    if signature_1022:
        sector[1022:1024] = SIGNATURE
    if not signature_510 and sector[510:512] == SIGNATURE:
        raise M07Error("undeclared signature at offset 510")
    if not signature_1022 and sector[1022:1024] == SIGNATURE:
        raise M07Error("undeclared signature at offset 1022")
    if sector[3:62] != base[3:62]:
        raise M07Error("probe changed a required BPB byte")
    return bytes(sector)


def offsets_to_ranges(offsets: list[int]) -> list[list[int]]:
    if not offsets:
        return []
    ranges = []
    start = previous = offsets[0]
    for offset in offsets[1:]:
        if offset != previous + 1:
            ranges.append([start, previous + 1])
            start = offset
        previous = offset
    ranges.append([start, previous + 1])
    return ranges


def validate_variant(base: bytes, candidate: bytes, item: dict, allowed_ranges: list[list[int]]) -> list[list[int]]:
    if len(candidate) != len(base) or len(candidate) != EXPECTED_BASE_RAW["size"]:
        raise M07Error("variant raw-image size differs")
    if candidate[1024:] != base[1024:]:
        raise M07Error("variant changed FAT, root directory, data area, or payload")
    changed = [index for index, (left, right) in enumerate(zip(base, candidate)) if left != right]
    allowed = set()
    for start, end in allowed_ranges:
        allowed.update(range(start, end))
    if any(offset not in allowed for offset in changed):
        raise M07Error("variant changed a byte outside its declared overlay mask")
    sector = candidate[:1024]
    if sector[3:62] != base[3:62]:
        raise M07Error("variant changed a BPB/layout byte")
    expected_510 = SIGNATURE if item["signature_510"] else None
    expected_1022 = SIGNATURE if item["signature_1022"] else None
    if (sector[510:512] == SIGNATURE) != bool(expected_510):
        raise M07Error("wrong signature bytes or offset at 510")
    if (sector[1022:1024] == SIGNATURE) != bool(expected_1022):
        raise M07Error("wrong signature bytes or offset at 1022")
    if item["probe"]:
        if sector[:3] != JUMP_BYTES or sector[PROBE_ENTRY:PROBE_ENTRY + len(PROBE_BYTES)] != PROBE_BYTES:
            raise M07Error("probe variant does not contain the declared probe")
    elif sector != base[:1024]:
        raise M07Error("V00 must retain the accepted M06 boot record exactly")
    return offsets_to_ranges(changed)


def build_variant(base: bytes, code: bytes, item: dict) -> tuple[bytes, list[list[int]]]:
    if item["probe"]:
        boot = make_probe_sector(base[:1024], code, item["signature_510"], item["signature_1022"])
        candidate = boot + base[1024:]
        allowed = [[0, 3], [62, 1024]]
    else:
        candidate = base
        allowed = []
    changed = validate_variant(base, candidate, item, allowed)
    return candidate, changed


def make_run(run_dir: Path) -> dict:
    cfg = preflight()
    if run_dir.exists():
        raise M07Error(f"M07 run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    probe = build_probe(run_dir / "probe")
    code = (run_dir / "probe/probe.bin").read_bytes()
    base_path = ROOT / "qa/results/m06/run-1/media/pc88va-m06-compile-only.img"
    base = base_path.read_bytes()
    common, builder, inspector = m05_modules()
    spec, derived = common.validate_spec(ROOT)
    variants = []
    for item in cfg["variants"]:
        variant_id = item["id"]
        output = run_dir / "variants" / variant_id
        output.mkdir(parents=True)
        raw, changed_ranges = build_variant(base, code, item)
        d88 = builder.build_d88(spec, raw)
        raw_path = output / f"{variant_id}.img"
        d88_path = output / f"{variant_id}.d88"
        raw_path.write_bytes(raw)
        d88_path.write_bytes(d88)
        d88_summary, extracted = inspector.parse_d88(d88, spec, derived)
        if extracted != raw:
            raise M07Error(f"D88-to-raw mismatch: {variant_id}")
        validate_variant(base, extracted, item, [[0, 3], [62, 1024]] if item["probe"] else [])
        manifest = {
            "changed_ranges": changed_ranges,
            "d88": identity(d88_path),
            "d88_sector_count": d88_summary["sector_count"],
            "d88_track_count": d88_summary["populated_tracks"],
            "id": variant_id,
            "probe": item["probe"],
            "raw": identity(raw_path),
            "round_trip": "byte-identical",
            "signature_510": item["signature_510"],
            "signature_1022": item["signature_1022"],
        }
        write_json(output / "manifest.json", manifest)
        variants.append(manifest)
    if variants[0]["raw"] != EXPECTED_BASE_RAW or variants[0]["d88"] != EXPECTED_BASE_D88:
        raise M07Error("V00 does not preserve accepted M06 media identities")
    result = {
        "claims": {
            "firmware_boot_acceptance": False,
            "hardware_validated": False,
            "m06_kernel_executed": False,
            "private_gate_ran": False,
        },
        "consumed_identities": {key: digest for key, (_, digest) in EXPECTED_IDENTITIES.items()},
        "m06_kernel": EXPECTED_KERNEL,
        "probe": probe,
        "schema_version": 1,
        "vaeg_public_contract": cfg["vaeg"],
        "variants": variants,
    }
    write_json(run_dir / "run-manifest.json", result)
    return result


def tree_snapshot(root: Path) -> list[dict]:
    return [
        {"path": path.relative_to(root).as_posix(), **identity(path)}
        for path in sorted(root.rglob("*")) if path.is_file()
    ]


def compare_runs(write: bool = True) -> dict:
    first = ROOT / RESULTS / "run-1"
    second = ROOT / RESULTS / "run-2"
    left = tree_snapshot(first)
    right = tree_snapshot(second)
    if left != right:
        raise M07Error("M07 public run trees differ")
    result = {"file_count": len(left), "result": "byte-identical", "schema_version": 1, "tree": left}
    if write:
        write_json(ROOT / RESULTS / "comparison.json", result)
    return result


def validate_public_result(value: dict) -> None:
    required = {
        "schema_version", "private_gate", "private_gate_result", "input_preservation",
        "variant_count", "trial_count", "resolved_field_count", "unresolved_field_count",
        "resolved_fields", "unresolved_fields", "public_promotion_status",
    }
    if set(value) != required or value.get("schema_version") != 1:
        raise M07Error("public result schema differs")
    resolved = value.get("resolved_fields")
    unresolved = value.get("unresolved_fields")
    if not isinstance(resolved, list) or not isinstance(unresolved, list):
        raise M07Error("public result field lists are invalid")
    if resolved != sorted(set(resolved)) or unresolved != sorted(set(unresolved)):
        raise M07Error("public result field names are not unique and sorted")
    if set(resolved) | set(unresolved) != set(QUESTION_FIELDS) or set(resolved) & set(unresolved):
        raise M07Error("public result does not partition the M07 question fields")
    if value.get("resolved_field_count") != len(resolved) or value.get("unresolved_field_count") != len(unresolved):
        raise M07Error("public result field counts differ")
    if value.get("variant_count") != 5 or not isinstance(value.get("trial_count"), int):
        raise M07Error("public result trial or variant count differs")
    if value.get("public_promotion_status") != "prohibited_pending_user_approval":
        raise M07Error("private overlay is missing its nonpromotion status")
    gate = value.get("private_gate")
    result = value.get("private_gate_result")
    preservation = value.get("input_preservation")
    trial_count = value.get("trial_count")
    if gate not in {"performed", "not_performed"}:
        raise M07Error("private gate status is invalid")
    if result not in {"conclusive", "inconclusive", "failed", "not_performed"}:
        raise M07Error("private gate result is invalid")
    if preservation not in {"passed", "failed", "not_performed"}:
        raise M07Error("private input-preservation result is invalid")
    if not isinstance(trial_count, int) or trial_count < 0:
        raise M07Error("private trial count is invalid")
    if gate == "not_performed" and (result != "not_performed" or preservation != "not_performed" or trial_count != 0):
        raise M07Error("not-performed public result is internally inconsistent")
    if gate == "performed" and (result == "not_performed" or preservation == "not_performed" or trial_count == 0):
        raise M07Error("performed public result is internally inconsistent")
    prohibited_keys = {"values", "winning_variant", "rom_sha256", "rom_basename", "trace", "registers", "entry_state"}
    if any(key in value for key in prohibited_keys):
        raise M07Error("public result contains a private-only field value")


def redact_private_result(private: dict) -> dict:
    if private.get("schema_version") != 1 or private.get("public_promotion_status") != "prohibited_pending_user_approval":
        raise M07Error("private result cannot be redacted safely")
    questions = private.get("questions")
    if not isinstance(questions, dict) or set(questions) != set(QUESTION_FIELDS):
        raise M07Error("private result question set differs")
    resolved = sorted(name for name, item in questions.items() if item.get("resolved") is True)
    unresolved = sorted(set(QUESTION_FIELDS) - set(resolved))
    result = {
        "input_preservation": private.get("input_preservation"),
        "private_gate": "performed",
        "private_gate_result": private.get("private_gate_result"),
        "public_promotion_status": "prohibited_pending_user_approval",
        "resolved_field_count": len(resolved),
        "resolved_fields": resolved,
        "schema_version": 1,
        "trial_count": private.get("trial_count"),
        "unresolved_field_count": len(unresolved),
        "unresolved_fields": unresolved,
        "variant_count": private.get("variant_count"),
    }
    validate_public_result(result)
    return result


def scan_public_text(text: str) -> None:
    lower = text.lower()
    markers = ("/users/", "file://", "pc88va-private-docs", "private-analysis-root", "secret-va.rom")
    if any(marker in lower for marker in markers):
        raise M07Error("tracked file contains a private path or synthetic firmware identity")


def public_data_paths() -> list[Path]:
    paths = [ROOT / CONFIG, ROOT / PUBLIC_SCHEMA, ROOT / PRIVATE_SCHEMA]
    if (ROOT / PUBLIC_RESULT).exists():
        paths.append(ROOT / PUBLIC_RESULT)
    paths.extend(sorted((ROOT / "docs/porting").glob("m07-*.md")))
    paths.extend(sorted((ROOT / "qa/golden").glob("m07-*.json")))
    return paths


def validate_public_workflow() -> None:
    text = (ROOT / ".github/workflows/m07-probe.yml").read_text(encoding="utf-8")
    lower = text.lower()
    forbidden = ("m07-private", "--roms", "m07_private_result", "pc88va_private_docs_root")
    if any(marker in lower for marker in forbidden):
        raise M07Error("public CI attempts private or VAEG execution")


def verify_or_enroll(enroll: bool) -> str:
    preflight()
    if load_json(ROOT / RESULTS / "comparison.json") != compare_runs(write=False):
        raise M07Error("M07 comparison evidence is stale")
    first = load_json(ROOT / RESULTS / "run-1/run-manifest.json")
    second = load_json(ROOT / RESULTS / "run-2/run-manifest.json")
    if first != second:
        raise M07Error("M07 public run manifests differ")
    if enroll:
        if (ROOT / GOLDEN).exists():
            raise M07Error("M07 golden already exists; enrollment never overwrites it")
        write_json(ROOT / GOLDEN, first)
    elif load_json(ROOT / GOLDEN) != first:
        raise M07Error("M07 public result differs from the committed golden")
    if (ROOT / PUBLIC_RESULT).exists():
        validate_public_result(load_json(ROOT / PUBLIC_RESULT))
    validate_public_workflow()
    for path in public_data_paths():
        scan_public_text(path.read_text(encoding="utf-8", errors="strict"))
    digest = identity(ROOT / GOLDEN)["sha256"]
    print(f"M07 public verification passed: golden={digest}")
    return str(digest)


def clean() -> None:
    target = (ROOT / RESULTS).resolve()
    if target != ROOT / "qa/results/m07" or target == ROOT or ROOT not in target.parents:
        raise M07Error("refusing unsafe M07 cleanup target")
    if target.exists():
        shutil.rmtree(target)
    print("M07 generated public result path cleaned")


def build_all() -> None:
    preflight()
    make_run(ROOT / RESULTS / "run-1")
    make_run(ROOT / RESULTS / "run-2")
    print("M07 probe and five public variants built twice")


def tests() -> None:
    result = run([sys.executable, "-m", "unittest", "discover", "-s", "tests/m07", "-p", "test_*.py"], check=False)
    if result.returncode:
        raise M07Error(f"M07 public tests failed: {result.stdout}{result.stderr}")
    print((result.stdout + result.stderr).strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--tests", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--enroll-golden", action="store_true")
    args = parser.parse_args()
    selected = [args.preflight, args.clean, args.build, args.compare, args.tests, args.verify, args.enroll_golden]
    if sum(selected) != 1:
        parser.error("select exactly one M07 action")
    try:
        if args.preflight:
            preflight()
            print("M07 public preflight passed")
        elif args.clean:
            clean()
        elif args.build:
            build_all()
        elif args.compare:
            compare_runs()
            print("M07 public comparison passed: complete trees are byte-identical")
        elif args.tests:
            tests()
        else:
            verify_or_enroll(args.enroll_golden)
    except (M07Error, OSError, ValueError) as exc:
        print(f"M07 ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
