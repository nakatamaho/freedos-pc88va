#!/usr/bin/env python3
"""Shared deterministic M02 contract and archive helpers."""

import hashlib
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath


M01R1_PARENT_COMMIT = "0ad3b0e33da66c552113c7389c8c81010a50f1f2"
PARENT_REPOSITORY = "https://github.com/nakatamaho/freedos-pc88va.git"
M01_MILESTONE = "M01-upstream-baseline-build"
M02_MILESTONE = "M02-baseline-artifact-bundle"
CANONICAL_PLATFORM = "nec98-baseline"
PURPOSE = "build-reference-only"

# These identify the accepted final M01R1 snapshot. Individual artifact and
# source-archive identities are read from the committed M01 golden below.
M01R1_COMMITTED_DIGESTS = {
    "components_lock": "440e481b28c740875489a6953a246ce5370c44074053c7aad3f80e79ec40c19c",
    "toolchain_lock": "39c5b3052d71463235a26e8704ab54c1fedb51ee75bb4efb55e6229391a95162",
    "m01_contract": "7d66be32b508395d8c36a902389f368e9f38d9abab08085bda89e3d2c5d6d578",
    "m01_golden": "6fcfe834f90ffc602589ddc63b50d90eba33bbc1802b6bff3c9ef6b9d397c7c3",
}

ROLE_ORDER = [
    "kernel",
    "kernel-alias",
    "system-transfer-tool",
    "kernel-country-driver",
    "boot-fat12",
    "boot-fat12-fallback",
    "boot-fat16",
    "boot-fat32",
    "command-interpreter",
    "standalone-country-driver",
]

ROLE_DESTINATIONS = {
    "kernel": ("fdkernel", "KERNEL.SYS"),
    "kernel-alias": ("fdkernel", "KWC8616.SYS"),
    "system-transfer-tool": ("fdkernel", "SYS.COM"),
    "kernel-country-driver": ("fdkernel", "COUNTRY.SYS"),
    "boot-fat12": ("fdkernel/boot", "B_FAT12.BIN"),
    "boot-fat12-fallback": ("fdkernel/boot", "B_FAT12F.BIN"),
    "boot-fat16": ("fdkernel/boot", "B_FAT16.BIN"),
    "boot-fat32": ("fdkernel/boot", "B_FAT32.BIN"),
    "command-interpreter": ("freecom", "COMMAND.COM"),
    "standalone-country-driver": ("fdos-country", "COUNTRY.SYS"),
}

COPY_METADATA = [
    ("metadata/components.lock.json", "manifests/components.lock.json", "components_lock"),
    ("metadata/toolchain-lock.json", "manifests/toolchains.lock.json", "toolchain_lock"),
    ("metadata/m01-build-contract.json", "manifests/m01-build-contract.json", "m01_contract"),
    ("metadata/m01-golden-manifest.json", "qa/golden/m01-baseline.json", "m01_golden"),
]

GENERATED_METADATA = (
    "metadata/artifact-manifest.json",
    "metadata/provenance.json",
    "metadata/consumer-contract.json",
)

CONSUMER_CONTRACT = {
    "schema_version": 1,
    "milestone": M02_MILESTONE,
    "platform": CANONICAL_PLATFORM,
    "purpose": PURPOSE,
    "claims": {
        "hardware_validated": False,
        "pc88va_bootable": False,
        "vaeg_validated": False,
    },
    "selection_rules": [
        "M05 and later consumers select artifacts by role, not by basename alone.",
        "Duplicate DOS basenames are legal across namespaces.",
        "No consumer may flatten the tree without an explicit collision policy.",
        "Neither country driver is selected as the VA runtime driver by M02.",
        "The four boot binaries are NEC98 baseline evidence and are not VA IPLs.",
        "Payload bytes must never be normalized, patched, timestamped or recompressed.",
    ],
}


class ValidationError(Exception):
    """A bounded fail-closed contract error."""


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value):
    reject_floats(value)
    try:
        text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"cannot encode canonical JSON: {exc}") from exc
    return (text + "\n").encode("utf-8")


def reject_floats(value):
    if isinstance(value, float):
        raise ValidationError("canonical JSON must not contain floating-point values")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValidationError("canonical JSON object keys must be strings")
            reject_floats(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            reject_floats(item)


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot parse JSON {path}: {exc}") from exc


def load_canonical_json(path):
    path = Path(path)
    value = load_json(path)
    actual = path.read_bytes()
    if actual.startswith(b"\xef\xbb\xbf"):
        raise ValidationError(f"canonical JSON has a UTF-8 BOM: {path}")
    if actual != canonical_json_bytes(value):
        raise ValidationError(f"JSON is not canonical: {path}")
    return value


def write_canonical_json(path, value):
    path = Path(path)
    ensure_dir(path.parent)
    path.write_bytes(canonical_json_bytes(value))
    os.chmod(path, 0o644)


def safe_posix_path(value, label="path"):
    if not isinstance(value, str) or not value or not value.isascii():
        raise ValidationError(f"{label} is not a non-empty ASCII path")
    if "\\" in value:
        raise ValidationError(f"{label} contains a backslash: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ValidationError(f"{label} is absolute or traverses a parent: {value!r}")
    if str(path) != value:
        raise ValidationError(f"{label} is not normalized: {value!r}")
    return value


def lstat_checked(path, label):
    path = Path(path)
    try:
        info = path.lstat()
    except OSError as exc:
        raise ValidationError(f"cannot stat {label} {path}: {exc}") from exc
    if stat.S_ISLNK(info.st_mode):
        raise ValidationError(f"symlink is not allowed for {label}: {path}")
    if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
        raise ValidationError(f"hard-linked input is not allowed for {label}: {path}")
    if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
        raise ValidationError(f"non-regular filesystem object is not allowed for {label}: {path}")
    return info


def ensure_dir(path, mode=0o755):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, mode)


def copy_regular_file(source, destination):
    source = Path(source)
    destination = Path(destination)
    source_info = lstat_checked(source, "M01 input artifact")
    if not stat.S_ISREG(source_info.st_mode):
        raise ValidationError(f"input is not a regular file: {source}")
    ensure_dir(destination.parent)
    try:
        with source.open("rb") as source_stream, destination.open("wb") as destination_stream:
            shutil.copyfileobj(source_stream, destination_stream, length=1024 * 1024)
        os.chmod(destination, 0o644)
    except OSError as exc:
        raise ValidationError(f"cannot copy {source} to {destination}: {exc}") from exc
    lstat_checked(destination, "bundle file")


def accepted_paths(root):
    root = Path(root)
    paths = {
        "components_lock": root / "manifests/components.lock.json",
        "toolchain_lock": root / "manifests/toolchains.lock.json",
        "m01_contract": root / "manifests/m01-build-contract.json",
        "m01_golden": root / "qa/golden/m01-baseline.json",
    }
    return paths


def component_identity(root):
    """Load component/contract/golden identity after checking top-level digests."""
    root = Path(root)
    paths = accepted_paths(root)
    for name, path in paths.items():
        expected = M01R1_COMMITTED_DIGESTS[name]
        if not path.is_file() or sha256_file(path) != expected:
            raise ValidationError(f"committed M01 {name} digest mismatch: {path}")
    lock = load_json(paths["components_lock"])
    contract = load_json(paths["m01_contract"])
    golden = load_json(paths["m01_golden"])
    if golden.get("schema_version") != 1 or golden.get("milestone") != M01_MILESTONE:
        raise ValidationError("committed M01 golden manifest is not the accepted M01R1 snapshot")
    if golden.get("canonical_platform") != "linux/amd64" or golden.get("comparison") != "byte-identical":
        raise ValidationError("committed M01 golden manifest has the wrong platform or comparison status")
    records = golden.get("artifacts")
    if not isinstance(records, list) or len(records) != 10:
        raise ValidationError("committed M01 golden manifest does not contain ten artifacts")
    if len({record.get("artifact") for record in records}) != len(records):
        raise ValidationError("committed M01 golden manifest contains duplicate artifact paths")
    if golden.get("contract_sha256") != M01R1_COMMITTED_DIGESTS["m01_contract"]:
        raise ValidationError("M01 golden build-contract identity is not accepted")
    if golden.get("toolchain_lock_sha256") != M01R1_COMMITTED_DIGESTS["toolchain_lock"]:
        raise ValidationError("M01 golden toolchain-lock identity is not accepted")
    source_archives = golden.get("source_archives")
    if not isinstance(source_archives, dict) or set(source_archives) != {"country", "fdkernel", "freecom"}:
        raise ValidationError("M01 golden source-archive map is incomplete")

    lock_components = lock.get("components")
    if not isinstance(lock_components, list) or len(lock_components) != 3:
        raise ValidationError("components lock does not contain three components")
    lock_by_path = {}
    for item in lock_components:
        path = item.get("path")
        if path in lock_by_path:
            raise ValidationError(f"duplicate component path in lock: {path}")
        lock_by_path[path] = item
    contract_components = contract.get("components")
    if not isinstance(contract_components, list) or len(contract_components) != 3:
        raise ValidationError("M01 build contract does not contain three components")
    contract_by_artifact = {}
    epochs = {}
    for component in contract_components:
        component_path = component.get("path")
        if component_path in epochs:
            raise ValidationError(f"duplicate M01 component contract: {component_path}")
        epoch = component.get("source_date_epoch")
        if not isinstance(epoch, int) or epoch < 0:
            raise ValidationError("committed M01 source epoch cannot be resolved unambiguously")
        epochs[component_path] = epoch
        lock_item = lock_by_path.get(component_path)
        if not lock_item or component.get("commit") != lock_item.get("commit"):
            raise ValidationError(f"M01 contract and component lock disagree: {component_path}")
        component_key = PurePosixPath(component_path).name
        if source_archives.get(component_key) is None:
            raise ValidationError(f"M01 source archive is missing for {component_key}")
        for artifact in component.get("required_artifacts", []):
            namespace = artifact.get("namespace")
            artifact_path = artifact.get("path")
            if not isinstance(namespace, str) or not isinstance(artifact_path, str):
                raise ValidationError("M01 required artifact contract is malformed")
            source_name = f"{namespace}/{artifact_path}"
            if source_name in contract_by_artifact:
                raise ValidationError(f"duplicate M01 required artifact: {source_name}")
            contract_by_artifact[source_name] = {
                "component_key": component_key,
                "component_path": component_path,
                "component_commit": component.get("commit"),
                "source_date_epoch": epoch,
                "m01_namespace": namespace,
                "m01_relative_path": artifact_path,
            }
    if set(contract_by_artifact) != {record.get("artifact") for record in records}:
        raise ValidationError("M01 golden and build-contract artifact path sets disagree")

    artifacts = []
    for record in records:
        required = ("artifact", "component_commit", "source_archive_sha256", "size", "sha256")
        if any(field not in record for field in required):
            raise ValidationError(f"M01 golden artifact record is incomplete: {record.get('artifact')}")
        source_name = record["artifact"]
        contract_item = contract_by_artifact[source_name]
        if record["component_commit"] != contract_item["component_commit"]:
            raise ValidationError(f"M01 golden component identity mismatch: {source_name}")
        if record["source_archive_sha256"] != source_archives[contract_item["component_key"]]:
            raise ValidationError(f"M01 golden source archive mismatch: {source_name}")
        if not isinstance(record["size"], int) or record["size"] < 0:
            raise ValidationError(f"M01 golden size is invalid: {source_name}")
        if not isinstance(record["sha256"], str) or re.fullmatch(r"[0-9a-f]{64}", record["sha256"]) is None:
            raise ValidationError(f"M01 golden SHA-256 is invalid: {source_name}")
        artifacts.append({**record, **contract_item})
    return {
        "paths": paths,
        "lock": lock,
        "contract": contract,
        "golden": golden,
        "artifacts": artifacts,
        "source_archives": source_archives,
        "epochs": epochs,
        "lock_by_path": lock_by_path,
    }


def role_for_artifact(item):
    namespace = item["m01_namespace"]
    basename = PurePosixPath(item["m01_relative_path"]).name.lower()
    if namespace == "fdkernel-nec98":
        names = {
            "kernel.sys": "kernel",
            "kwc8616.sys": "kernel-alias",
            "sys.com": "system-transfer-tool",
            "b_fat12.bin": "boot-fat12",
            "b_fat12f.bin": "boot-fat12-fallback",
            "b_fat16.bin": "boot-fat16",
            "b_fat32.bin": "boot-fat32",
        }
    elif namespace == "fdkernel-country" and basename == "country.sys":
        names = {basename: "kernel-country-driver"}
    elif namespace == "freecom-nec98-japanese" and basename == "command.com":
        names = {basename: "command-interpreter"}
    elif namespace == "fdos-country" and basename == "country.sys":
        names = {basename: "standalone-country-driver"}
    else:
        names = {}
    role = names.get(basename)
    if role is None:
        raise ValidationError(f"M01 artifact has no M02 logical role: {item['artifact']}")
    return role


def m02_artifacts(authority):
    records = []
    seen_roles = set()
    seen_bundle_paths = set()
    for item in authority["artifacts"]:
        role = role_for_artifact(item)
        if role in seen_roles:
            raise ValidationError(f"duplicate M02 manifest role: {role}")
        seen_roles.add(role)
        directory, basename = ROLE_DESTINATIONS[role]
        bundle_path = f"payload/{directory}/{basename}"
        if bundle_path in seen_bundle_paths:
            raise ValidationError(f"duplicate M02 bundle path: {bundle_path}")
        seen_bundle_paths.add(bundle_path)
        records.append(
            {
                "role": role,
                "component_namespace": {
                    "fdkernel": "fdkernel",
                    "freecom": "freecom",
                    "country": "fdos-country",
                }[item["component_key"]],
                "original_m01_source_path": item["artifact"],
                "bundle_path": bundle_path,
                "size": item["size"],
                "sha256": item["sha256"],
                "component_commit": item["component_commit"],
                "source_archive_sha256": item["source_archive_sha256"],
                "source_date_epoch": item["source_date_epoch"],
                "m01_namespace": item["m01_namespace"],
            }
        )
    if seen_roles != set(ROLE_ORDER):
        raise ValidationError(f"M02 logical role set mismatch: {sorted(seen_roles)}")
    return sorted(records, key=lambda record: ROLE_ORDER.index(record["role"]))


def validate_artifact_contract_records(records):
    roles = [record.get("role") for record in records]
    paths = [record.get("bundle_path") for record in records]
    if len(roles) != len(set(roles)):
        raise ValidationError("duplicate manifest role")
    if len(paths) != len(set(paths)):
        raise ValidationError("duplicate bundle path")
    for path in paths:
        safe_posix_path(path, "bundle path")


def flatten_collision(records):
    basenames = {}
    for record in records:
        basename = PurePosixPath(record["bundle_path"]).name
        if basename in basenames and basenames[basename] != record["bundle_path"]:
            raise ValidationError(f"basename collision during flatten attempt: {basename}")
        basenames[basename] = record["bundle_path"]


def validate_m01_input(m01_run, authority):
    m01_run = Path(m01_run)
    manifest_path = m01_run / "manifest.json"
    artifact_root = m01_run / "artifacts"
    if not manifest_path.is_file() or not artifact_root.is_dir():
        raise ValidationError(
            "verified M01 results are missing; run make m01-image, make m01-build, "
            "make m01-compare, and make m01-verify before running M02"
        )
    manifest = load_json(manifest_path)
    golden = authority["golden"]
    if manifest.get("artifact_count") != 10 or manifest.get("milestone") != M01_MILESTONE:
        raise ValidationError("M01 input manifest is not the accepted ten-artifact result")
    if manifest.get("canonical_platform") != "linux/amd64":
        raise ValidationError("M01 input platform is not linux/amd64")
    if manifest.get("contract_sha256") != golden.get("contract_sha256") or manifest.get("toolchain_lock_sha256") != golden.get("toolchain_lock_sha256"):
        raise ValidationError("M01 input lock or contract identity is stale")
    if manifest.get("source_archives") != golden.get("source_archives") or manifest.get("artifacts") != golden.get("artifacts"):
        raise ValidationError("M01 input manifest does not match the committed M01 golden")

    expected_paths = {item["artifact"] for item in authority["artifacts"]}
    expected_directories = {"."}
    for relative in expected_paths:
        path = PurePosixPath(relative)
        for index in range(1, len(path.parts)):
            expected_directories.add("/".join(path.parts[:index]))
    actual_paths = set()
    actual_directories = {"."}
    for current, directories, files in os.walk(artifact_root, topdown=True, followlinks=False):
        current_path = Path(current)
        lstat_checked(current_path, "M01 artifact directory")
        for directory in directories:
            directory_path = current_path / directory
            lstat_checked(directory_path, "M01 artifact directory")
            actual_directories.add(directory_path.relative_to(artifact_root).as_posix())
        for filename in files:
            path = current_path / filename
            lstat_checked(path, "M01 input artifact")
            relative = path.relative_to(artifact_root).as_posix()
            safe_posix_path(relative, "M01 artifact path")
            actual_paths.add(relative)
    if actual_paths != expected_paths:
        raise ValidationError(
            f"M01 artifact path set mismatch: missing={sorted(expected_paths - actual_paths)}, "
            f"extra={sorted(actual_paths - expected_paths)}"
        )
    if actual_directories != expected_directories:
        raise ValidationError(
            f"M01 artifact directory set mismatch: missing={sorted(expected_directories - actual_directories)}, "
            f"extra={sorted(actual_directories - expected_directories)}"
        )
    for item in authority["artifacts"]:
        path = artifact_root / PurePosixPath(item["artifact"])
        info = lstat_checked(path, "M01 input artifact")
        if info.st_size != item["size"] or sha256_file(path) != item["sha256"]:
            raise ValidationError(f"M01 artifact identity mismatch: {item['artifact']}")
    country = [item for item in authority["artifacts"] if PurePosixPath(item["artifact"]).name.lower() == "country.sys"]
    if len(country) != 2 or country[0]["sha256"] == country[1]["sha256"]:
        raise ValidationError("M01 country.sys identities are not two distinct artifacts")
    return manifest


def archive_epoch_policy(authority):
    if set(authority["epochs"]) != {item["component_path"] for item in authority["artifacts"]}:
        raise ValidationError("committed M01 source epoch set is incomplete or ambiguous")
    by_component = {}
    for item in authority["artifacts"]:
        by_component[item["component_key"]] = item["source_date_epoch"]
    if set(by_component) != {"fdkernel", "freecom", "country"}:
        raise ValidationError("committed M01 source epoch set is incomplete or ambiguous")
    metadata_epoch = min(by_component.values())
    return by_component, metadata_epoch


def artifact_manifest(root, authority, artifacts, component_epochs, metadata_epoch):
    metadata_files = []
    for bundle_path, source_path, digest_name in COPY_METADATA:
        source = Path(root) / source_path
        if sha256_file(source) != M01R1_COMMITTED_DIGESTS[digest_name]:
            raise ValidationError(f"committed metadata digest changed: {source_path}")
        metadata_files.append(
            {
                "path": bundle_path,
                "source_path": source_path,
                "size": source.stat().st_size,
                "sha256": M01R1_COMMITTED_DIGESTS[digest_name],
            }
        )
    return {
        "schema_version": 1,
        "milestone": M02_MILESTONE,
        "source_milestone": M01_MILESTONE,
        "platform": CANONICAL_PLATFORM,
        "purpose": PURPOSE,
        "pc88va_bootable": False,
        "hardware_validated": False,
        "vaeg_validated": False,
        "artifacts": artifacts,
        "metadata_files": metadata_files,
        "archive_entry_mtime_policy": {
            "payload": "Use the producing component source_date_epoch from the committed M01 build contract.",
            "directories_and_metadata": "Use the minimum of the three committed M01 component source_date_epoch values.",
            "metadata_epoch": metadata_epoch,
        },
    }


def provenance(authority, component_epochs, metadata_epoch):
    components = []
    for component_key in ("country", "fdkernel", "freecom"):
        item = authority["lock_by_path"][next(path for path in authority["lock_by_path"] if PurePosixPath(path).name == component_key)]
        components.append(
            {
                "name": component_key,
                "path": item["path"],
                "branch": item["branch"],
                "commit": item["commit"],
                "source_archive_sha256": authority["source_archives"][component_key],
                "source_date_epoch": component_epochs[component_key],
            }
        )
    return {
        "schema_version": 1,
        "milestone": M02_MILESTONE,
        "source_milestone": M01_MILESTONE,
        "parent": {"repository": PARENT_REPOSITORY, "accepted_m01r1_commit": M01R1_PARENT_COMMIT},
        "platform": CANONICAL_PLATFORM,
        "purpose": PURPOSE,
        "m01_evidence": {
            "components_lock_sha256": M01R1_COMMITTED_DIGESTS["components_lock"],
            "toolchain_lock_sha256": M01R1_COMMITTED_DIGESTS["toolchain_lock"],
            "build_contract_sha256": M01R1_COMMITTED_DIGESTS["m01_contract"],
            "golden_manifest_sha256": M01R1_COMMITTED_DIGESTS["m01_golden"],
            "source_archives": authority["source_archives"],
        },
        "archive_mtime": {
            "payload_component_epochs": {key: component_epochs[key] for key in ("country", "fdkernel", "freecom")},
            "metadata_and_directory_epoch": metadata_epoch,
        },
        "input": {"m01_result": "qa/results/m01/run-1"},
    }


def tree_entries(bundle_root):
    bundle_root = Path(bundle_root)
    if not bundle_root.is_dir():
        raise ValidationError(f"bundle root is missing: {bundle_root}")
    entries = []
    for current, directories, files in os.walk(bundle_root, topdown=True, followlinks=False):
        current_path = Path(current)
        lstat_checked(current_path, "bundle directory")
        for directory in directories:
            path = current_path / directory
            info = lstat_checked(path, "bundle directory")
            relative = path.relative_to(bundle_root.parent).as_posix()
            safe_posix_path(relative, "bundle path")
            entries.append((relative, "directory", info.st_size, None))
        for filename in files:
            path = current_path / filename
            info = lstat_checked(path, "bundle file")
            relative = path.relative_to(bundle_root.parent).as_posix()
            safe_posix_path(relative, "bundle path")
            entries.append((relative, "file", info.st_size, sha256_file(path)))
    root_relative = bundle_root.relative_to(bundle_root.parent).as_posix()
    entries.append((root_relative, "directory", bundle_root.stat().st_size, None))
    return sorted(entries, key=lambda item: item[0])


def expected_bundle_paths(artifacts):
    files = [item["bundle_path"] for item in artifacts]
    files.extend(item[0] for item in COPY_METADATA)
    files.extend(GENERATED_METADATA)
    paths = {"baseline-artifact-bundle"}
    for relative in files:
        path = PurePosixPath("baseline-artifact-bundle") / relative
        for index in range(1, len(path.parts) + 1):
            paths.add("/".join(path.parts[:index]))
    return paths


def archive_mtime_for(path, artifacts, component_epochs, metadata_epoch):
    relative = PurePosixPath(path)
    if len(relative.parts) >= 3 and relative.parts[0:2] == ("baseline-artifact-bundle", "payload"):
        bundle_path = "/".join(relative.parts[1:])
        for item in artifacts:
            if item["bundle_path"] == bundle_path:
                return component_epochs[item["component_namespace"] if item["component_namespace"] != "fdos-country" else "country"]
    return metadata_epoch


def create_tar(bundle_root, archive_path, artifacts, component_epochs, metadata_epoch):
    bundle_root = Path(bundle_root)
    archive_path = Path(archive_path)
    ensure_dir(archive_path.parent)
    try:
        with tarfile.open(archive_path, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            for relative, entry_type, _, _ in tree_entries(bundle_root):
                source = bundle_root.parent / PurePosixPath(relative)
                info = tarfile.TarInfo(relative)
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                info.mtime = archive_mtime_for(relative, artifacts, component_epochs, metadata_epoch)
                info.pax_headers = {}
                if entry_type == "directory":
                    info.type = tarfile.DIRTYPE
                    info.mode = 0o755
                    info.size = 0
                    archive.addfile(info)
                else:
                    info.type = tarfile.REGTYPE
                    info.mode = 0o644
                    info.size = source.stat().st_size
                    with source.open("rb") as stream:
                        archive.addfile(info, stream)
        os.chmod(archive_path, 0o644)
    except (OSError, tarfile.TarError) as exc:
        raise ValidationError(f"cannot create deterministic USTAR archive: {exc}") from exc


def write_sha256_sidecar(archive_path, sidecar_path):
    archive_path = Path(archive_path)
    sidecar_path = Path(sidecar_path)
    sidecar_path.write_bytes(f"{sha256_file(archive_path)}  {archive_path.name}\n".encode("ascii"))
    os.chmod(sidecar_path, 0o644)


def reject_generated_metadata_values(value, label="metadata"):
    forbidden_keys = {"generated_at", "created_at", "updated_at", "wall_clock", "wall_clock_timestamp"}
    timestamp_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:")
    if isinstance(value, dict):
        for key, item in value.items():
            if key in forbidden_keys:
                raise ValidationError(f"wall-clock metadata key is not allowed: {label}.{key}")
            reject_generated_metadata_values(item, f"{label}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            reject_generated_metadata_values(item, f"{label}[{index}]")
    elif isinstance(value, str):
        if value.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", value):
            raise ValidationError(f"absolute path is not allowed in generated metadata: {label}")
        if timestamp_pattern.match(value):
            raise ValidationError(f"wall-clock timestamp is not allowed in generated metadata: {label}")


def validate_repository_identity(root):
    root = Path(root).resolve()
    if root.name != "freedos-pc88va":
        raise ValidationError(f"repository basename is not freedos-pc88va: {root.name}")
    try:
        actual_root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=root, text=True).strip()).resolve()
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        subprocess.run(["git", "merge-base", "--is-ancestor", M01R1_PARENT_COMMIT, head], cwd=root, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        origin = subprocess.check_output(["git", "remote", "get-url", "origin"], cwd=root, text=True).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValidationError(f"parent identity check failed: {exc}") from exc
    if actual_root != root:
        raise ValidationError(f"repository root mismatch: {actual_root}")
    accepted_origins = {PARENT_REPOSITORY, PARENT_REPOSITORY.removesuffix(".git")}
    if origin not in accepted_origins:
        raise ValidationError(f"parent origin mismatch: {origin!r}")
    authority = component_identity(root)
    for component_key, item in ((PurePosixPath(path).name, value) for path, value in authority["lock_by_path"].items()):
        component_path = root / item["path"]
        try:
            gitmodules_url = subprocess.check_output(["git", "config", "-f", ".gitmodules", f"submodule.{item['path']}.url"], cwd=root, text=True).strip()
            gitmodules_branch = subprocess.check_output(["git", "config", "-f", ".gitmodules", f"submodule.{item['path']}.branch"], cwd=root, text=True).strip()
            stage = subprocess.check_output(["git", "ls-files", "--stage", "--", item["path"]], cwd=root, text=True).split()
            actual = subprocess.check_output(["git", "-C", str(component_path), "rev-parse", "HEAD"], text=True).strip()
            status = subprocess.check_output(["git", "-C", str(component_path), "status", "--porcelain=v1", "--untracked-files=all"], text=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ValidationError(f"component identity check failed for {component_key}: {exc}") from exc
        if gitmodules_url != item.get("repository") or gitmodules_branch != item.get("branch"):
            raise ValidationError(f".gitmodules component policy mismatch for {component_key}")
        if len(stage) < 2 or stage[0] != "160000" or stage[1] != item["commit"] or actual != item["commit"]:
            raise ValidationError(f"parent gitlink mismatch for {component_key}")
        if status:
            raise ValidationError(f"component worktree is dirty: {item['path']}: {status.strip()}")
    return authority


def validate_host_capability():
    if platform.system() not in {"Darwin", "Linux"}:
        raise ValidationError(f"M02 host portability is limited to macOS and Linux: {platform.system()}")
    if sys.version_info < (3, 9):
        raise ValidationError("M02 requires Python 3.9 or newer")


def remove_owned_results(root):
    result_root = Path(root) / "qa/results/m02"
    if result_root.is_symlink() or (result_root.exists() and not result_root.is_dir()):
        raise ValidationError(f"M02 result root is not a normal directory: {result_root}")
    for path in (result_root / "run-1", result_root / "run-2", result_root / "comparison.json"):
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
    ensure_dir(result_root)


def compare_tree_roots(first_root, second_root):
    first = {entry[0]: entry for entry in tree_entries(first_root)}
    second = {entry[0]: entry for entry in tree_entries(second_root)}
    errors = []
    if set(first) != set(second):
        errors.append({"type": "path-set-mismatch", "run_1_only": sorted(set(first) - set(second)), "run_2_only": sorted(set(second) - set(first))})
    for path in sorted(set(first) & set(second)):
        if first[path][1] != second[path][1]:
            errors.append({"type": "entry-type-mismatch", "path": path})
        elif first[path][1] == "file" and first[path][2:] != second[path][2:]:
            errors.append({"type": "file-byte-mismatch", "path": path, "run_1": {"size": first[path][2], "sha256": first[path][3]}, "run_2": {"size": second[path][2], "sha256": second[path][3]}})
    return errors


def snapshot_for_golden(run_root, artifacts):
    run_root = Path(run_root)
    bundle_root = run_root / "baseline-artifact-bundle"
    tree = []
    for path, entry_type, size, digest in tree_entries(bundle_root):
        item = {"path": path, "type": entry_type}
        if entry_type == "file":
            item.update({"size": size, "sha256": digest})
        tree.append(item)
    metadata = []
    for path in sorted(GENERATED_METADATA + tuple(item[0] for item in COPY_METADATA)):
        file_path = bundle_root / PurePosixPath(path)
        metadata.append({"path": path, "size": file_path.stat().st_size, "sha256": sha256_file(file_path)})
    archive = run_root / "baseline-artifact-bundle.tar"
    sidecar = run_root / "baseline-artifact-bundle.tar.sha256"
    return {
        "schema_version": 1,
        "milestone": M02_MILESTONE,
        "platform": CANONICAL_PLATFORM,
        "comparison": "byte-identical",
        "artifacts": artifacts,
        "metadata": metadata,
        "tree": tree,
        "archive": {
            "path": archive.name,
            "size": archive.stat().st_size,
            "sha256": sha256_file(archive),
            "sidecar_path": sidecar.name,
            "sidecar_size": sidecar.stat().st_size,
            "sidecar_sha256": sha256_file(sidecar),
        },
    }
