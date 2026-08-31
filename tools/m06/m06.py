#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Build, compare, and verify the reproducible M06 PC-88VA kernel target."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = Path("config/m06/kernel-build.json")
CURRENT_LOCK = Path("manifests/m06-components.lock.json")
INTERFACE_SCHEMA = Path("schema/m06-kernel-interface.schema.json")
GOLDEN = Path("qa/golden/m06-kernel-manifest.json")
RESULTS = Path("qa/results/m06")
IMAGE_TAG = "freedos-pc88va-m01:local"
PC88VA_COMMIT = "69ccdd8699895722fc537d647ec490685532bdc4"
PC88VA_PARENT = "6523acdb87f4665e6068ea331859885267242005"
SOURCE_ARCHIVE_SHA256 = "d9cc6113cfe297040a7e94f9df70320c52b1f09bf59fb2e7b30e59ddc5001535"
FREECOM_COMMIT = "855281a3114b43ad4b8d9a320f2aca39be046bba"
COUNTRY_COMMIT = "23f189cca3420606eae8723884fa92ccd65eb307"
START_COMMIT = "b41acd3765497498945954756349548c831c7915"
OLD_KERNEL_SHA256 = "3ebddb01abe5e39f16d27439836be283c57d454f012d3c990f01fa8a2b14101d"
IDENTITIES = {
    "components_lock": ("manifests/components.lock.json", "440e481b28c740875489a6953a246ce5370c44074053c7aad3f80e79ec40c19c"),
    "toolchain_lock": ("manifests/toolchains.lock.json", "39c5b3052d71463235a26e8704ab54c1fedb51ee75bb4efb55e6229391a95162"),
    "m01_contract": ("manifests/m01-build-contract.json", "7d66be32b508395d8c36a902389f368e9f38d9abab08085bda89e3d2c5d6d578"),
    "m01_golden": ("qa/golden/m01-baseline.json", "6fcfe834f90ffc602589ddc63b50d90eba33bbc1802b6bff3c9ef6b9d397c7c3"),
    "m02r1_golden": ("qa/golden/m02/bundle-manifest.json", "4d4e92f92911130109b5b140b2202fc1dfc3abb9af3cd7501b685894d0cb78fd"),
    "m03r1_golden": ("qa/golden/m03/port-surface.json", "d871c7f188313218c2c9481ea9fe7c6abf6acd6369f996b2641021ad27c80550"),
    "m04_contract": ("config/contracts/m04-provisional-pc88va-boot-media.json", "f2e4efdc9d9e3a31dc100b81896427beeaeaca29d36d692b5dfeb5fb459460f4"),
    "m04_schema": ("config/contracts/m04-provisional-pc88va-boot-media.schema.json", "f50c099211e2e70f959fb1cc70e93553699f9862113b50c7cda7f29816e6b7c0"),
    "m04_evidence": ("config/contracts/m04-evidence-matrix.json", "0612699d305738f2db131cb87c5fa7e9393b206672d6bec27483a602e7e91770"),
    "m05_specification": ("config/m05/media.json", "f8ba0e41300ee6e11d7a1f0cf646e335a09df243afc8e1235efade3d17cd06bc"),
    "m05_schema": ("config/m05/media.schema.json", "0380d30bec213ade393390498510176fcb14a4f904dd6a9c9c22cee50646fd0f"),
    "m05_golden": ("qa/golden/m05-media-manifest.json", "b81c7bfdde36df76edfd9e802c22d90c865329f206c7bbb9dae2ddbe39e4abaa"),
    "copying": ("COPYING", "0f1e68d9b4a580cdcca4c5f4e3b8046f7a8759da05edd109cff081bc484b3c4b"),
}
EXPECTED_GITLINKS = {
    "components/fdkernel": PC88VA_COMMIT,
    "components/freecom": FREECOM_COMMIT,
    "components/country": COUNTRY_COMMIT,
}
EXPECTED_M05 = {
    "pc88va-m05-candidate.img": (1310720, "507dec28446e82fc69062feb6790998b609fcbfe0bc79941e3f8f22284fb82c8"),
    "pc88va-m05-candidate.d88": (1331888, "163e17bd192f22654465a9f61a7c5c411f0aad4160bc020b8522b7e51a62f313"),
}
EXPECTED_UNCHANGED_PAYLOADS = {
    "COMMAND.COM": (91143, "fabe7744cc7c51c6f72519cc39d89bf77beaf908f994675a97a1e34c93549da1"),
    "COUNTRY.SYS": (42614, "04b2d2bc8df382090686f00e547d718d6706d22fb34c34dd77cd55083d5c34d5"),
}
PRIVATE_MARKERS = (
    "pc88va-private-docs", "private-evidence", "private-analysis", "varom",
    "user-owned-dump", "/users/", "file://",
)


class M06Error(RuntimeError):
    """Raised when an M06 acceptance invariant fails."""


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise M06Error(f"cannot parse JSON {path}: {exc}") from exc
    if canonical_bytes(value) != path.read_bytes():
        raise M06Error(f"JSON is not canonical: {path}")
    return value


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identity(path: Path, relative: str | None = None) -> dict[str, object]:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise M06Error(f"unsafe or missing regular file: {path}")
    data = path.read_bytes()
    result: dict[str, object] = {"sha256": sha256_bytes(data), "size": len(data)}
    if relative is not None:
        result["path"] = relative
    return result


def git(*args: str, cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(("git", *args), cwd=cwd, check=False, capture_output=True, text=True)
    if check and result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise M06Error(f"git {' '.join(args)} failed: {detail}")
    return result


def command(args: list[str], *, cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=cwd, check=False, capture_output=True, text=True)
    if check and result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise M06Error(f"command failed ({' '.join(args)}): {detail}")
    return result


def gitlink(path: str) -> str:
    fields = git("ls-files", "--stage", "--", path).stdout.strip().split()
    if len(fields) < 4 or fields[0] != "160000":
        raise M06Error(f"path is not an indexed gitlink: {path}")
    return fields[1]


def validate_current_lock(lock: dict) -> None:
    if lock.get("schema_version") != 1 or lock.get("status") != "current-m06":
        raise M06Error("M06 current component lock schema or status is invalid")
    components = lock.get("components")
    if not isinstance(components, list) or len(components) != 3:
        raise M06Error("M06 current component lock must contain three components")
    by_path = {item.get("path"): item for item in components if isinstance(item, dict)}
    if set(by_path) != set(EXPECTED_GITLINKS):
        raise M06Error("M06 current component lock path set differs")
    for path, expected in EXPECTED_GITLINKS.items():
        if by_path[path].get("commit") != expected:
            raise M06Error(f"M06 current component lock commit differs: {path}")
    expected_repositories = {
        "components/fdkernel": "https://github.com/nakatamaho/fdkernel.git",
        "components/freecom": "https://github.com/nakatamaho/freecom_dbcs2.git",
        "components/country": "https://github.com/FDOS/country.git",
    }
    for path, repository in expected_repositories.items():
        if by_path[path].get("repository") != repository:
            raise M06Error(f"M06 current component repository differs: {path}")
    fdkernel = by_path["components/fdkernel"]
    if (
        fdkernel.get("branch") != "necpc88va"
        or fdkernel.get("parent_commit") != PC88VA_PARENT
        or fdkernel.get("source_archive_sha256") != SOURCE_ARCHIVE_SHA256
    ):
        raise M06Error("M06 fdkernel provenance in current lock differs")
    historical = lock.get("historical_components_lock", {})
    if historical.get("path") != "manifests/components.lock.json" or historical.get("sha256") != IDENTITIES["components_lock"][1]:
        raise M06Error("M06 lock does not preserve the historical components lock")


def validate_component_state(require_remote: bool = True) -> None:
    for path, expected in EXPECTED_GITLINKS.items():
        if gitlink(path) != expected:
            raise M06Error(f"parent gitlink mismatch: {path}")
        component = ROOT / path
        if git("rev-parse", "HEAD", cwd=component).stdout.strip() != expected:
            raise M06Error(f"component checkout mismatch: {path}")
        if git("status", "--short", "--untracked-files=all", cwd=component).stdout:
            raise M06Error(f"component worktree is dirty: {path}")
    if git("merge-base", "--is-ancestor", PC88VA_PARENT, PC88VA_COMMIT, cwd=ROOT / "components/fdkernel", check=False).returncode:
        raise M06Error("PC-88VA child is not a descendant of the accepted fdkernel parent")
    if require_remote:
        result = git("ls-remote", "--heads", "origin", "refs/heads/necpc88va", cwd=ROOT / "components/fdkernel")
        fields = result.stdout.strip().split()
        if len(fields) != 2 or fields[0] != PC88VA_COMMIT:
            raise M06Error("remote necpc88va branch does not expose the accepted child commit")


def validate_accepted_identities(contract: dict) -> None:
    if contract.get("schema_version") != 1 or contract.get("parent_start_commit") != START_COMMIT:
        raise M06Error("M06 build contract identity is invalid")
    if contract.get("component_identity", {}).get("commit") != PC88VA_COMMIT:
        raise M06Error("M06 build contract child identity differs")
    for key, (relative, expected) in IDENTITIES.items():
        actual = identity(ROOT / relative)["sha256"]
        if actual != expected or contract.get("consumed_identities", {}).get(key) != expected:
            raise M06Error(f"accepted identity mismatch: {relative}: {actual}")
    if git("merge-base", "--is-ancestor", START_COMMIT, "HEAD", check=False).returncode:
        raise M06Error("accepted M05 parent is not an ancestor of HEAD")


def validate_m05_regression() -> None:
    run = ROOT / "qa/results/m05/run-1"
    for name, (size, digest) in EXPECTED_M05.items():
        observed = identity(run / name)
        if observed != {"sha256": digest, "size": size}:
            raise M06Error(f"accepted M05 generated identity differs: {name}")
    raw = (run / "pc88va-m05-candidate.img").read_bytes()
    if raw[:3] != b"\xeb\xfe\x90" or any(raw[62:1024]):
        raise M06Error("M05 boot placeholder or zero padding changed")
    if raw[510:512] == b"\x55\xaa" or raw[1022:1024] == b"\x55\xaa":
        raise M06Error("M05 contains an undeclared boot signature")
    inspection = load_json(run / "inspection-manifest.json")
    for allocation in inspection.get("regions", {}).get("allocations", []):
        if not allocation.get("fat_timestamp", {}).get("utc"):
            raise M06Error("M05 FAT timestamp evidence is missing")


def preflight(require_remote: bool = True, require_m05_results: bool = True) -> dict:
    if ROOT.name != "freedos-pc88va" or Path(git("rev-parse", "--show-toplevel").stdout.strip()).resolve() != ROOT:
        raise M06Error("repository root identity mismatch")
    contract = load_json(ROOT / CONTRACT)
    validate_accepted_identities(contract)
    validate_current_lock(load_json(ROOT / CURRENT_LOCK))
    validate_component_state(require_remote=require_remote)
    if require_m05_results:
        validate_m05_regression()
    image = command(["docker", "image", "inspect", IMAGE_TAG, "--format", "{{.Architecture}} {{.Id}}"])
    if not image.stdout.startswith("amd64 sha256:"):
        raise M06Error("accepted M01 Linux/amd64 image is unavailable or wrong-architecture")
    config = ROOT / "qa/results/m01/run-1/input-staging/fdkernel-nec98.mak"
    if not config.is_file() or config.is_symlink() or "KERNEL_BUILD_DATE" not in config.read_text(encoding="utf-8"):
        raise M06Error("verified M01 deterministic fdkernel configuration is unavailable")
    suffix = "M05 bytes, and " if require_m05_results else ""
    print(f"M06 preflight passed: current child, historical identities, {suffix}amd64 toolchain image are valid")
    return contract


def create_source_archive(runtime: Path) -> Path:
    archive = runtime / "fdkernel.tar"
    with archive.open("wb") as stream:
        result = subprocess.run(
            ("git", "archive", "--format=tar", "--prefix=fdkernel/", PC88VA_COMMIT),
            cwd=ROOT / "components/fdkernel",
            check=False,
            stdout=stream,
            stderr=subprocess.PIPE,
        )
    if result.returncode:
        raise M06Error(f"cannot archive PC-88VA child: {result.stderr.decode('utf-8', 'replace').strip()}")
    os.chmod(archive, 0o444)
    if identity(archive)["sha256"] != SOURCE_ARCHIVE_SHA256:
        raise M06Error("PC-88VA child source archive identity differs")
    return archive


def container_script() -> str:
    return """set -eu
rm -rf /work/src
mkdir -p /work/src /output/kernel/compiled /output/kernel/nec98
tar -xf /input/fdkernel.tar -C /work/src
cd /work/src/fdkernel/pc88va
wmake -ms -h -f makefile.wc clean all >/output/pc88va.log 2>&1
python3 tools/collect_build.py --repo-root /work/src/fdkernel --output /output/kernel/evidence --component-commit 69ccdd8699895722fc537d647ec490685532bdc4 --source-archive-sha256 d9cc6113cfe297040a7e94f9df70320c52b1f09bf59fb2e7b30e59ddc5001535
cp build/startup.obj build/stubs.obj build/platform.lib build/KVA8616.exe bin/KERNEL.SYS bin/KVA8616.SYS /output/kernel/compiled/
cd /work/src/fdkernel/nec98
cp /input/fdkernel-nec98.mak config.mak
env -u XUPX -u UPXOPT make clobber COMPILER=owlinux >/output/nec98.log 2>&1
env -u XUPX -u UPXOPT make all COMPILER=owlinux >>/output/nec98.log 2>&1
cp bin/kernel.sys bin/KWC8616.sys bin/sys.com bin/country.sys boot/b_fat12.bin boot/b_fat12f.bin boot/b_fat16.bin boot/b_fat32.bin /output/kernel/nec98/
"""


def docker_copy(container_id: str, source: str, destination: Path) -> None:
    result = command(["docker", "cp", f"{container_id}:{source}", str(destination)], check=False)
    if result.returncode:
        raise M06Error(f"cannot copy container evidence {source}: {result.stderr.strip()}")


def build_kernel_run(run_dir: Path, runtime: Path, archive: Path, source_epoch: int) -> None:
    if run_dir.exists():
        raise M06Error(f"M06 run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    created = command([
        "docker", "create", "--platform", "linux/amd64", "--entrypoint", "/bin/bash",
        "--env", f"SOURCE_DATE_EPOCH={source_epoch}", IMAGE_TAG, "-lc", container_script(),
    ])
    container_id = created.stdout.strip()
    if not container_id:
        raise M06Error("docker create did not return a container ID")
    try:
        command(["docker", "cp", str(archive), f"{container_id}:/input/fdkernel.tar"])
        command([
            "docker", "cp", str(ROOT / "qa/results/m01/run-1/input-staging/fdkernel-nec98.mak"),
            f"{container_id}:/input/fdkernel-nec98.mak",
        ])
        started = command(["docker", "start", "-a", container_id], check=False)
        log_path = runtime / f"{run_dir.name}-outer.log"
        log_path.write_text(started.stdout + started.stderr, encoding="utf-8")
        if started.returncode:
            for name in ("pc88va.log", "nec98.log"):
                docker_copy(container_id, f"/output/{name}", runtime / f"{run_dir.name}-{name}")
            raise M06Error(f"M06 container build failed for {run_dir.name}: status {started.returncode}")
        docker_copy(container_id, "/output/kernel/.", run_dir / "kernel")
        for name in ("pc88va.log", "nec98.log"):
            docker_copy(container_id, f"/output/{name}", runtime / f"{run_dir.name}-{name}")
    finally:
        command(["docker", "rm", container_id], check=False)


def validate_tool_identities(compile_manifest: dict) -> None:
    lock = json.loads((ROOT / "manifests/toolchains.lock.json").read_text(encoding="utf-8"))
    expected = {
        item["name"]: {"sha256": item["sha256"], "size": item["size"]}
        for item in lock["canonical"]["open_watcom"]["host_tools"]
    }
    observed = compile_manifest.get("tools", {})
    for name in ("wcc", "wmake", "wlink", "wlib"):
        if observed.get(name) != expected[name]:
            raise M06Error(f"Open Watcom tool identity differs: {name}")
    nasm = observed.get("nasm")
    if not isinstance(nasm, dict) or not isinstance(nasm.get("size"), int) or len(nasm.get("sha256", "")) != 64:
        raise M06Error("NASM identity is missing from the compile manifest")


def validate_kernel_role(kernel: dict[str, object]) -> None:
    if kernel.get("sha256") == OLD_KERNEL_SHA256 or kernel.get("size") == 83774:
        raise M06Error("PC-88VA target is a renamed or conflated NEC98 kernel")


def validate_stub_ledger(ledger: dict, source: str) -> None:
    interfaces = ledger.get("interfaces")
    if ledger.get("failure_return") != -1 or not isinstance(interfaces, list) or len(interfaces) != 10:
        raise M06Error("M06 temporary stub ledger is incomplete")
    names = [item.get("name") for item in interfaces if isinstance(item, dict)]
    if len(set(names)) != 10:
        raise M06Error("M06 temporary stub ledger contains a duplicate name")
    for item in interfaces:
        if (
            not re.fullmatch(r"M(?:0[789]|1[0-7])", str(item.get("removal_milestone", "")))
            or item.get("name") not in source
            or item.get("marker") not in source
        ):
            raise M06Error("M06 temporary stub is unlisted, unbounded, or absent from source")
    lowered = source.lower()
    if any(token in lowered for token in ("__int__", "outp(", "inp(", "#pragma aux", "_asm")):
        raise M06Error("M06 temporary stub source contains hardware or firmware-call machinery")


def validate_pc_kernel(run_dir: Path) -> dict:
    compiled = run_dir / "kernel/compiled"
    kernel = identity(compiled / "KERNEL.SYS")
    alias = identity(compiled / "KVA8616.SYS")
    executable = identity(compiled / "KVA8616.exe")
    if kernel != alias or kernel != executable:
        raise M06Error("PC-88VA kernel aliases are not byte-identical")
    validate_kernel_role(kernel)
    evidence_dir = run_dir / "kernel/evidence"
    compile_manifest = load_json(evidence_dir / "compile-manifest.json")
    interface = load_json(evidence_dir / "kernel-interface.json")
    build_evidence = load_json(evidence_dir / "build-evidence.json")
    symbols = load_json(evidence_dir / "symbol-evidence.json")
    validate_tool_identities(compile_manifest)
    if compile_manifest.get("component_commit") != PC88VA_COMMIT or compile_manifest.get("target_macros") != ["DBCS", "JAPAN", "PC88VA"]:
        raise M06Error("PC-88VA compile manifest component or macro set differs")
    if any("nec98" in item.get("source", "").lower() or "ibmpc" in item.get("source", "").lower() for item in compile_manifest.get("objects", [])):
        raise M06Error("PC-88VA compile manifest contains another platform path")
    if compile_manifest.get("link_inputs_in_order") != ["pc88va/build/startup.obj", "pc88va/build/platform.lib"]:
        raise M06Error("PC-88VA ordered link inputs differ")
    if interface.get("artifact", {}).get("sha256") != kernel["sha256"] or interface.get("binary", {}).get("container") != "dos-mz":
        raise M06Error("kernel interface record does not match the linked MZ artifact")
    if interface.get("physical_load_address", {}).get("status") != "unknown":
        raise M06Error("M06 fabricated a physical kernel load address")
    names = {item.get("name") for item in symbols.get("symbols", [])}
    if not {"_pc88va_compile_only_entry", "_pc88va_compile_only_fatal_stop", "pc88va_platform_probe_"}.issubset(names):
        raise M06Error("canonical symbol evidence lacks the compile-only entry or fatal stop")
    ledger = load_json(ROOT / "components/fdkernel/pc88va/config/stubs.json")
    source = (ROOT / "components/fdkernel/pc88va/kernel/stubs.c").read_text(encoding="utf-8")
    validate_stub_ledger(ledger, source)
    expected_stub_symbols = {f"{item['name']}_" for item in ledger["interfaces"]}
    if not expected_stub_symbols.issubset(names) or build_evidence.get("stub_count") != 10:
        raise M06Error("M06 temporary stub count differs")
    return {"artifact": kernel, "build_evidence": build_evidence, "interface": interface}


def validate_nec98(run_dir: Path, contract: dict) -> list[dict]:
    result = []
    for name, expected in sorted(contract["historical_nec98_artifacts"].items()):
        observed = identity(run_dir / "kernel/nec98" / name)
        if observed["sha256"] != expected:
            raise M06Error(f"NEC98 regression identity differs: {name}")
        result.append({"name": name, **observed})
    return result


def load_m05_modules():
    m05 = str(ROOT / "tools/m05")
    if m05 not in sys.path:
        sys.path.insert(0, m05)
    import common as m05_common  # type: ignore
    import build_media as m05_builder  # type: ignore
    import inspect_media as m05_inspector  # type: ignore
    return m05_common, m05_builder, m05_inspector


def install_m05_overlay(common) -> None:
    """Let immutable M05 tools consume the exact current M06 child checkout."""
    historical = {
        "country": COUNTRY_COMMIT,
        "fdkernel": PC88VA_PARENT,
        "freecom": FREECOM_COMMIT,
    }
    current = {
        "country": COUNTRY_COMMIT,
        "fdkernel": PC88VA_COMMIT,
        "freecom": FREECOM_COMMIT,
    }
    def validate_historical_contract(component_gitlinks: dict) -> None:
        if component_gitlinks != historical:
            raise M06Error("M05 specification component identities changed")

    common.EXPECTED_GITLINKS = current
    common.validate_component_contract = validate_historical_contract


def validate_m05_spec_for_m06(common):
    """Validate immutable M05 data while the exact M06 child gitlink is active."""
    install_m05_overlay(common)
    return common.validate_spec(ROOT)


def prepare_m05_results() -> None:
    """Regenerate accepted M05 bytes without altering its historical builder files."""
    preflight(require_m05_results=False)
    common, builder, inspector = load_m05_modules()
    install_m05_overlay(common)
    common.remove_owned_results(ROOT)
    result_root = ROOT / "qa/results/m05"
    for name in ("run-1", "run-2"):
        run_dir = result_root / name
        builder.build_once(ROOT, run_dir)
        inspector.inspect_run(ROOT, run_dir, True)
    import compare_media as comparator  # type: ignore
    comparison = comparator.compare_runs(result_root / "run-1", result_root / "run-2")
    if comparison.get("status") != "pass":
        raise M06Error("accepted M05 prerequisite regeneration is not byte-identical")
    common.write_canonical_json(result_root / "comparison.json", comparison)
    result = command([sys.executable, "tools/m05/verify_m05.py", "--verify"], check=False)
    if result.returncode:
        raise M06Error(f"accepted M05 prerequisite verification failed: {result.stdout}{result.stderr}")
    validate_m05_regression()
    print("M06 prepared accepted M05 prerequisite bytes: two runs and historical golden verify exactly")


def m06_records(kernel_path: Path):
    common, _, _ = load_m05_modules()
    spec, derived = validate_m05_spec_for_m06(common)
    records = common.accepted_artifacts(ROOT, spec)
    kernel_identity = identity(kernel_path)
    validate_kernel_role(kernel_identity)
    output = []
    replaced = 0
    for source in records:
        item = dict(source)
        if item["dos_name"] == "KERNEL.SYS":
            item.update({
                "bundle_path": "generated/m06/pc88va/KERNEL.SYS",
                "component_commit": PC88VA_COMMIT,
                "component_namespace": "fdkernel-pc88va",
                "runtime_claim": "compile-only PC-88VA scaffold; no boot or runtime claim",
                "sha256": kernel_identity["sha256"],
                "size": kernel_identity["size"],
                "source_path": kernel_path,
                "source_role": "pc88va-compile-only-kernel",
            })
            replaced += 1
        output.append(item)
    if replaced != 1:
        raise M06Error("M06 did not replace exactly one KERNEL.SYS payload role")
    for item in output:
        if item["dos_name"] in EXPECTED_UNCHANGED_PAYLOADS:
            expected = EXPECTED_UNCHANGED_PAYLOADS[item["dos_name"]]
            if (item["size"], item["sha256"]) != expected:
                raise M06Error(f"unchanged M05 payload identity differs: {item['dos_name']}")
    return common, spec, derived, output


def public_record(record: dict) -> dict:
    return {
        key: record[key]
        for key in (
            "bundle_path", "component_commit", "component_namespace", "dos_name",
            "runtime_claim", "sha256", "size", "source_date_epoch", "source_role",
        )
    }


def build_media_run(run_dir: Path, contract: dict) -> None:
    media_dir = run_dir / "media"
    if media_dir.exists():
        raise M06Error(f"M06 media output already exists: {media_dir}")
    media_dir.mkdir()
    kernel_path = run_dir / "kernel/compiled/KERNEL.SYS"
    common, spec, derived, records = m06_records(kernel_path)
    _, builder, inspector = load_m05_modules()
    raw, regions = builder.build_raw_image(spec, derived, records)
    d88 = builder.build_d88(spec, raw)
    raw_path = media_dir / contract["media"]["raw_filename"]
    d88_path = media_dir / contract["media"]["d88_filename"]
    raw_path.write_bytes(raw)
    d88_path.write_bytes(d88)
    expected_records = [inspector.expected_record(item) for item in records]
    inspected_regions, extracted = inspector.inspect_raw(raw, spec, derived, expected_records)
    d88_summary, reconstructed = inspector.validate_d88_round_trip(d88, raw, spec, derived)
    if reconstructed != raw:
        raise M06Error("M06 D88 extraction differs from the derived raw image")
    extracted_dir = media_dir / "extracted"
    extracted_dir.mkdir()
    for name, data in sorted(extracted.items()):
        (extracted_dir / name).write_bytes(data)
    (media_dir / "extracted-raw.img").write_bytes(reconstructed)
    build_manifest = {
        "claims": {
            "boot_record_executes": False,
            "command_com_runs": False,
            "firmware_boot_accepted": False,
            "hardware_validated": False,
            "kernel_runtime_validated": False,
            "vaeg_validated": False,
        },
        "derived_layout": derived,
        "inputs": [public_record(item) for item in records],
        "m05_golden_sha256": IDENTITIES["m05_golden"][1],
        "m05_specification_sha256": IDENTITIES["m05_specification"][1],
        "milestone": "M06-pc88va-kernel-compile-target",
        "pc88va_kernel": identity(kernel_path),
        "regions": regions,
        "schema_version": 1,
        "d88": {**identity(d88_path), "populated_tracks": spec["d88"]["populated_tracks"], "sector_count": derived["total_sectors"]},
        "raw": identity(raw_path),
    }
    inspection_manifest = {
        "d88": d88_summary,
        "derived_layout": derived,
        "extracted_payloads": [
            {"dos_name": name, "sha256": sha256_bytes(data), "size": len(data)}
            for name, data in sorted(extracted.items())
        ],
        "extracted_raw": identity(media_dir / "extracted-raw.img"),
        "milestone": "M06-pc88va-kernel-compile-target",
        "raw": identity(raw_path),
        "regions": inspected_regions,
        "schema_version": 1,
        "validation": {
            "d88_structure": "pass",
            "fat12_structure": "pass",
            "payload_extraction": "pass",
            "raw_d88_round_trip": "byte-identical",
        },
    }
    write_json(media_dir / "build-manifest.json", build_manifest)
    write_json(media_dir / "inspection-manifest.json", inspection_manifest)
    write_json(run_dir / "run-manifest.json", make_run_manifest(run_dir, contract))


def make_run_manifest(run_dir: Path, contract: dict) -> dict:
    pc = validate_pc_kernel(run_dir)
    nec = validate_nec98(run_dir, contract)
    media = run_dir / "media"
    build = load_json(media / "build-manifest.json")
    inspection = load_json(media / "inspection-manifest.json")
    return {
        "component_lock_sha256": identity(ROOT / CURRENT_LOCK)["sha256"],
        "contract_sha256": identity(ROOT / CONTRACT)["sha256"],
        "kernel": pc,
        "media": {
            "build_manifest_sha256": identity(media / "build-manifest.json")["sha256"],
            "builder_regions": build["regions"],
            "d88": build["d88"],
            "inspected_regions": inspection["regions"],
            "inspection_manifest_sha256": identity(media / "inspection-manifest.json")["sha256"],
            "payloads": inspection["extracted_payloads"],
            "raw": build["raw"],
        },
        "milestone": "M06-pc88va-kernel-compile-target",
        "nec98_regression": nec,
        "schema_sha256": identity(ROOT / INTERFACE_SCHEMA)["sha256"],
        "schema_version": 1,
        "source_archive_sha256": SOURCE_ARCHIVE_SHA256,
    }


def build_all() -> None:
    contract = preflight()
    result_root = ROOT / RESULTS
    runtime = result_root / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    archive = create_source_archive(runtime)
    for name in ("run-1", "run-2"):
        build_kernel_run(result_root / name, runtime, archive, contract["build"]["source_date_epoch"])
    print("M06 kernel builds completed: two isolated PC-88VA and NEC98 runs generated")


def media_all() -> None:
    contract = preflight()
    for name in ("run-1", "run-2"):
        build_media_run(ROOT / RESULTS / name, contract)
    print("M06 derived media built: PC-88VA compile-only kernel replaced the NEC98 packaging reference")


def tree_snapshot(root: Path) -> list[dict]:
    if root.is_symlink() or not root.is_dir():
        raise M06Error(f"M06 run tree is missing or unsafe: {root}")
    output = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise M06Error(f"symlink in M06 run tree: {relative}")
        if stat.S_ISDIR(info.st_mode):
            output.append({"path": relative, "type": "directory"})
        elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
            output.append({"path": relative, **identity(path), "type": "file"})
        else:
            raise M06Error(f"unsupported M06 run entry: {relative}")
    return output


def compare_runs(write: bool = True) -> dict:
    first_root = ROOT / RESULTS / "run-1"
    second_root = ROOT / RESULTS / "run-2"
    first = tree_snapshot(first_root)
    second = tree_snapshot(second_root)
    errors = []
    if first != second:
        first_by = {item["path"]: item for item in first}
        second_by = {item["path"]: item for item in second}
        for relative in sorted(set(first_by) | set(second_by)):
            if first_by.get(relative) != second_by.get(relative):
                errors.append({"path": relative, "run_1": first_by.get(relative), "run_2": second_by.get(relative)})
                if len(errors) == 20:
                    break
    result = {
        "byte_identical": not errors,
        "errors": errors,
        "milestone": "M06-pc88va-kernel-compile-target",
        "run_1": first,
        "run_2": second,
        "schema_version": 1,
        "status": "pass" if not errors else "fail",
    }
    if write:
        write_json(ROOT / RESULTS / "comparison.json", result)
    if errors:
        raise M06Error(f"M06 two-run comparison failed: {errors[:3]}")
    print("M06 comparison passed: objects, library, MZ, evidence, media, and extracted payloads are byte-identical")
    return result


def validate_interface_schema(interface: dict) -> None:
    schema = load_json(ROOT / INTERFACE_SCHEMA)
    if schema.get("type") != "object" or schema.get("properties", {}).get("target", {}).get("const") != "pc88va":
        raise M06Error("M06 kernel-interface schema shape is invalid")
    required = schema.get("required", [])
    if any(key not in interface for key in required):
        raise M06Error("kernel-interface record lacks a schema-required field")
    if interface.get("target") != "pc88va" or interface.get("entry_symbol") != "_pc88va_compile_only_entry":
        raise M06Error("kernel-interface target or entry symbol differs")


def verify_run(run_dir: Path, contract: dict) -> dict:
    recorded = load_json(run_dir / "run-manifest.json")
    recomputed = make_run_manifest(run_dir, contract)
    if recorded != recomputed:
        raise M06Error(f"M06 run manifest is stale: {run_dir.name}")
    validate_interface_schema(recorded["kernel"]["interface"])
    media = run_dir / "media"
    _, spec, derived, records = m06_records(run_dir / "kernel/compiled/KERNEL.SYS")
    _, _, inspector = load_m05_modules()
    raw = (media / contract["media"]["raw_filename"]).read_bytes()
    d88 = (media / contract["media"]["d88_filename"]).read_bytes()
    regions, extracted = inspector.inspect_raw(raw, spec, derived, [inspector.expected_record(item) for item in records])
    _, reconstructed = inspector.validate_d88_round_trip(d88, raw, spec, derived)
    if reconstructed != raw or regions != recorded["media"]["inspected_regions"]:
        raise M06Error("fresh M05 inspector disagrees with M06 media evidence")
    for name, data in extracted.items():
        if (media / "extracted" / name).read_bytes() != data:
            raise M06Error(f"stored M06 extracted payload differs: {name}")
    return recorded


def verify_or_enroll(enroll: bool) -> str:
    contract = preflight()
    recorded_comparison = load_json(ROOT / RESULTS / "comparison.json")
    if recorded_comparison != compare_runs(write=False):
        raise M06Error("M06 comparison evidence is stale")
    first = verify_run(ROOT / RESULTS / "run-1", contract)
    second = verify_run(ROOT / RESULTS / "run-2", contract)
    if first != second:
        raise M06Error("M06 run manifests differ")
    golden_path = ROOT / GOLDEN
    if enroll:
        if golden_path.exists():
            raise M06Error("M06 golden already exists; enrollment never overwrites it")
        write_json(golden_path, first)
        print(f"M06 golden enrolled explicitly: {identity(golden_path)['sha256']}")
    else:
        if load_json(golden_path) != first:
            raise M06Error("M06 result differs from the committed golden")
        print(f"M06 verification passed: golden={identity(golden_path)['sha256']}")
    return str(identity(golden_path)["sha256"])


def validate_tracked_safety() -> None:
    forbidden_suffixes = {".rom", ".d88", ".img", ".bin", ".obj", ".o", ".lib", ".exe", ".sys", ".tar", ".log"}
    forbidden = []
    for relative in [item for item in git("ls-files", "-z").stdout.split("\0") if item]:
        lower = relative.lower()
        if Path(lower).suffix in forbidden_suffixes or lower.startswith("qa/results/"):
            forbidden.append(relative)
        if any(marker in lower for marker in PRIVATE_MARKERS):
            forbidden.append(relative)
    if forbidden:
        raise M06Error("forbidden generated or private tracked path: " + ", ".join(sorted(set(forbidden))))


def negative_tests() -> None:
    validate_tracked_safety()
    result = command([
        sys.executable, "-m", "unittest", "discover", "-s", "tests/m06", "-p", "test_*.py"
    ], check=False)
    if result.returncode:
        raise M06Error(f"M06 negative tests failed: {result.stdout}{result.stderr}")
    print(result.stdout.strip())


def clean() -> None:
    target = (ROOT / RESULTS).resolve()
    if target != ROOT / "qa/results/m06" or target == ROOT or ROOT not in target.parents:
        raise M06Error("refusing unsafe M06 cleanup target")
    if target.exists():
        shutil.rmtree(target)
    print("M06 generated result path cleaned")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight", action="store_true")
    modes.add_argument("--clean", action="store_true")
    modes.add_argument("--build", action="store_true")
    modes.add_argument("--prepare-m05", action="store_true")
    modes.add_argument("--nec98-regression", action="store_true")
    modes.add_argument("--media", action="store_true")
    modes.add_argument("--compare", action="store_true")
    modes.add_argument("--negative-tests", action="store_true")
    modes.add_argument("--enroll-golden", action="store_true")
    modes.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        if args.preflight:
            preflight()
        elif args.clean:
            clean()
        elif args.build:
            build_all()
        elif args.prepare_m05:
            prepare_m05_results()
        elif args.nec98_regression:
            contract = preflight()
            for name in ("run-1", "run-2"):
                validate_nec98(ROOT / RESULTS / name, contract)
            print("M06 NEC98 regression passed: 8 accepted fdkernel artifacts match in both runs")
        elif args.media:
            media_all()
        elif args.compare:
            compare_runs()
        elif args.negative_tests:
            negative_tests()
        else:
            verify_or_enroll(args.enroll_golden)
    except (M06Error, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"M06 failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
