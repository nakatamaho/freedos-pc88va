#!/usr/bin/env python3
"""Build and bind two identical M15 stage-2 loader artifacts.

The profile is an explicit input. Private profiles and every generated product
must remain in ignored, persistent evidence storage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
CHILD = ROOT / "components/fdkernel"
BUILDER = CHILD / "pc88va/tools/build_loader.py"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identify(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {"size": len(data), "sha256": sha256(data)}


def git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def private_sink(path: Path) -> None:
    resolved = path.resolve()
    evidence = (ROOT / ".private-evidence").resolve()
    if resolved != evidence and evidence not in resolved.parents:
        raise ValueError("Private loader outputs must stay under ignored .private-evidence")
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise ValueError("Loader output path must not traverse a symlink")
    ignored = subprocess.run(
        ["git", "-C", str(ROOT), "check-ignore", "-q", str(resolved / "sink-probe")],
        check=False,
    )
    if ignored.returncode:
        raise ValueError("Private loader output directory is not Git-ignored")
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError("Private loader output directory must be owner-only")


def source_identity() -> dict[str, object]:
    state = git("status", "--porcelain", "--untracked-files=no", cwd=CHILD)
    if state:
        raise ValueError("fdkernel tracked source is dirty")
    files = [CHILD / "pc88va/tools/build_loader.py", CHILD / "pc88va/tools/loader_profile.py"]
    files.extend(sorted(p for p in (CHILD / "pc88va/boot").rglob("*")
                        if p.is_file() and p.suffix in (".asm", ".inc")))
    return {
        "fdkernel_commit": git("rev-parse", "HEAD", cwd=CHILD),
        "source_files": {
            p.relative_to(CHILD).as_posix(): identify(p)
            for p in files
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overlay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-loader", type=Path)
    parser.add_argument("--stage1-extent", type=Path)
    parser.add_argument("--expected-stage1", type=Path)
    args = parser.parse_args()

    overlay = args.overlay.resolve(strict=True)
    if overlay.is_symlink() or not overlay.is_file():
        parser.error("overlay must be a regular file")
    overlay_data = json.loads(overlay.read_text(encoding="utf-8"))
    overlay_class = overlay_data.get("layout", {}).get("profile_class")
    private = overlay_class == "private_observation_overlay"
    output = args.output.resolve()
    if output.exists() or output.is_symlink():
        parser.error("output directory must not already exist")
    output.mkdir(mode=0o700 if private else 0o755, parents=True)
    if private:
        private_sink(output)

    nasm = shutil.which("nasm")
    if not nasm:
        raise ValueError("nasm is not available on PATH")
    nasm_path = Path(nasm).resolve(strict=True)
    nasm_version = subprocess.check_output([str(nasm_path), "-v"], text=True).strip()
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PATH"] = str(nasm_path.parent) + os.pathsep + env.get("PATH", "")

    extent = None
    if args.stage1_extent:
        extent_path = args.stage1_extent.resolve(strict=True)
        extent = json.loads(extent_path.read_text(encoding="utf-8"))
        if set(extent) != {"first_lba", "sector_count", "file_size"}:
            raise ValueError("stage-1 extent fields differ from the loader contract")
    if args.expected_stage1 and not extent:
        raise ValueError("stage-1 reference comparison requires an explicit stage-1 extent")

    run_records = []
    for number in (1, 2):
        run = output / f"run-{number}"
        stages = [(2, None)]
        if extent:
            stages.append((1, extent))
        run_record = {}
        for stage, stage_extent in stages:
            command = [sys.executable, "-B", str(BUILDER), "--overlay", str(overlay),
                       "--output", str(run), "--stage", str(stage)]
            if stage_extent:
                extent_file = output / "stage1-extent.json"
                if not extent_file.exists():
                    extent_file.write_text(json.dumps(stage_extent, sort_keys=True) + "\n",
                                           encoding="utf-8")
                    extent_file.chmod(0o600 if private else 0o644)
                command.extend(("--extent", str(extent_file)))
            result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True)
            (output / f"run-{number}-stage-{stage}.log").write_bytes(result.stdout + result.stderr)
            if result.returncode:
                raise ValueError("loader build failed; details remain in the selected output sink")
            artifact = run / f"stage{stage}.bin"
            manifest = run / f"stage{stage}-manifest.json"
            if not artifact.is_file() or not manifest.is_file():
                raise ValueError("loader build did not produce its artifact and stage manifest")
            run_record[f"stage{stage}"] = {
                "artifact": identify(artifact),
                "stage_manifest_sha256": sha256(manifest.read_bytes()),
            }
        run_records.append(run_record)

    stages_to_compare = [2, 1] if extent else [2]
    equal = all(
        (output / f"run-1/stage{stage}.bin").read_bytes()
        == (output / f"run-2/stage{stage}.bin").read_bytes()
        and (output / f"run-1/stage{stage}-manifest.json").read_bytes()
        == (output / f"run-2/stage{stage}-manifest.json").read_bytes()
        for stage in stages_to_compare
    )
    if not equal:
        raise ValueError("independent loader builds differ")

    expected_record = None
    if args.expected_loader:
        expected = args.expected_loader.resolve(strict=True)
        if expected.is_symlink() or not expected.is_file():
            raise ValueError("expected loader must be a regular file")
        expected_record = identify(expected)
        if (output / "run-1/stage2.bin").read_bytes() != expected.read_bytes():
            raise ValueError("rebuilt loader differs from the supplied reference")

    expected_stage1_record = None
    if args.expected_stage1:
        expected_stage1 = args.expected_stage1.resolve(strict=True)
        if expected_stage1.is_symlink() or not expected_stage1.is_file():
            raise ValueError("expected stage 1 must be a regular file")
        reference = bytearray(expected_stage1.read_bytes())
        built = bytearray((output / "run-1/stage1.bin").read_bytes())
        if len(reference) != 1024 or len(built) != 1024:
            raise ValueError("stage-1 comparison requires 1024-byte references")
        # The media composer owns the BPB and the two boot-signature slots.
        for start, end in ((3, 62), (510, 512), (1022, 1024)):
            reference[start:end] = bytes(end - start)
            built[start:end] = bytes(end - start)
        if reference != built:
            raise ValueError("rebuilt stage 1 differs outside media-owned BPB/signature fields")
        expected_stage1_record = {
            "artifact": identify(expected_stage1),
            "matches_after_media_owned_fields_are_masked": True,
        }

    record = {
        "format": "m15-stage2-loader-build-pair-v1",
        "overlay_class": overlay_class,
        "overlay_sha256": sha256(overlay.read_bytes()),
        "recipe": {
            "parent_commit": git("rev-parse", "HEAD"),
            "makefile_sha256": sha256((ROOT / "Makefile").read_bytes()),
            "runner_sha256": sha256(Path(__file__).read_bytes()),
        },
        "source": source_identity(),
        "toolchain": {
            "nasm_path_sha256": sha256(nasm_path.read_bytes()),
            "nasm_version": nasm_version,
            "python_executable_sha256": sha256(Path(sys.executable).read_bytes()),
            "python_version": sys.version,
        },
        "stage1_extent": extent,
        "builds": run_records,
        "two_builds_byte_identical": True,
        "reference_loader": expected_record,
        "reference_byte_identical": expected_record is not None,
        "reference_stage1": expected_stage1_record,
    }
    record_path = output / "build-record.json"
    record_path.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    record_path.chmod(0o600 if private else 0o644)
    print("M15 loader stage builds are byte-identical" +
          (" and match the supplied references" if expected_record or expected_stage1_record else ""))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"M15 loader build failed: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(1)
