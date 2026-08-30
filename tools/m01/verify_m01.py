#!/usr/bin/env python3
"""Run the offline M01 structure, identity, and evidence checks."""

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path


EXPECTED_FIXED_COMMITS = {
    "components/freecom": "855281a3114b43ad4b8d9a320f2aca39be046bba",
    "components/country": "23f189cca3420606eae8723884fa92ccd65eb307",
}
EXPECTED_SUBMODULES = {
    "components/fdkernel": ("https://github.com/nakatamaho/fdkernel.git", "nec98-current"),
    "components/freecom": ("https://github.com/nakatamaho/freecom_dbcs2.git", "deterministic-build-timestamp"),
    "components/country": ("https://github.com/FDOS/country.git", "master"),
}
REQUIRED_FILES = {
    ".github/workflows/m01-baseline.yml",
    "containers/m01/Dockerfile",
    "containers/m01/README.md",
    "containers/m01/build-entrypoint.sh",
    "config/m01/environment.env",
    "config/m01/fdkernel-nec98.mak",
    "config/m01/freecom-build-timestamp.json",
    "docs/build/M01-toolchain.md",
    "docs/build/macos-apple-silicon.md",
    "docs/build/upstream-build-contracts.md",
    "docs/decisions/0001-m01-canonical-toolchain.md",
    "docs/milestones/M01-upstream-baseline-build.md",
    "manifests/m01-build-contract.json",
    "manifests/components.lock.json",
    "manifests/toolchains.lock.json",
    "qa/golden/m01-baseline.json",
    "qa/host/m01/README.md",
    "tools/m01/build_baseline.sh",
    "tools/m01/host_fs.py",
    "tools/m01/test_image_identity.py",
    "tools/m01/container/image_tool_probe.sh",
    "tools/m01/test_host_portability.sh",
    "tools/m01/test_freecom_timestamp.py",
    "tools/m01/collect_artifacts.py",
    "tools/m01/compare_runs.py",
    "tools/m01/verify_m01.py",
    "tools/m01/freecom_timestamp.py",
}
EXPECTED_FDKERNEL_TEMPLATE = "# Deterministic M01 configuration for the pinned NEC98 baseline.\nXNASM=nasm\nXCPU=86\nXFAT=16\n"
EXPECTED_FDKERNEL_ARTIFACTS = [
    ("fdkernel-nec98", "nec98/bin/kernel.sys"),
    ("fdkernel-nec98", "nec98/bin/KWC8616.sys"),
    ("fdkernel-nec98", "nec98/bin/sys.com"),
    ("fdkernel-country", "nec98/bin/country.sys"),
    ("fdkernel-nec98", "nec98/boot/b_fat12f.bin"),
    ("fdkernel-nec98", "nec98/boot/b_fat12.bin"),
    ("fdkernel-nec98", "nec98/boot/b_fat16.bin"),
    ("fdkernel-nec98", "nec98/boot/b_fat32.bin"),
]
EXPECTED_FREECOM_TIMESTAMP = {
    "component": "freecom",
    "source_date_epoch": 1740233872,
    "timezone": "UTC",
    "formatted_date": "Feb 22 2025",
    "formatted_time": "14:17:52",
    "date_macro": "FREECOM_BUILD_DATE",
    "time_macro": "FREECOM_BUILD_TIME",
    "wmake_configuration_variable": "CFLAGS2",
}
FORBIDDEN_SUFFIXES = {
    ".com", ".exe", ".obj", ".o", ".lib", ".a", ".map", ".sym", ".lst", ".err",
    ".rom", ".bin", ".d88", ".d98", ".hdi", ".hdd", ".img", ".ima", ".iso",
    ".zip", ".7z", ".tar", ".tgz", ".gz",
}


def run_git(root, *arguments, check=True):
    return subprocess.run(["git", *arguments], cwd=root, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def load_json(path):
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def digest(path):
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def fail(errors, message):
    errors.append(message)


def assert_equal(errors, label, actual, expected):
    if actual != expected:
        fail(errors, f"{label}: expected {expected!r}, got {actual!r}")


def component_commits(root, errors):
    path = root / "manifests/components.lock.json"
    try:
        lock = load_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        fail(errors, f"components lock cannot be parsed: {exc}")
        return {}
    components = lock.get("components")
    if lock.get("schema_version") != 1 or lock.get("status") != "scaffold" or not isinstance(components, list) or len(components) != 3:
        fail(errors, "components lock schema or component count is invalid")
        return {}
    result = {}
    for item in components:
        path_value = item.get("path") if isinstance(item, dict) else None
        commit = item.get("commit") if isinstance(item, dict) else None
        if path_value in result or not isinstance(path_value, str) or not re.fullmatch(r"[0-9a-f]{40}", str(commit)):
            fail(errors, "components lock contains a duplicate or invalid commit")
        else:
            result[path_value] = commit
    for path_value, expected in EXPECTED_FIXED_COMMITS.items():
        assert_equal(errors, f"components lock fixed commit for {path_value}", result.get(path_value), expected)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.repo_root.resolve()
    errors = []
    expected_commits = component_commits(root, errors)
    if "components/fdkernel" not in expected_commits:
        fail(errors, "components lock is missing the fdkernel commit")

    if root.name != "freedos-pc88va":
        fail(errors, f"repository basename is not freedos-pc88va: {root.name}")
    try:
        actual_root = Path(run_git(root, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
        if actual_root != root:
            fail(errors, f"repository root mismatch: {actual_root}")
    except subprocess.CalledProcessError as exc:
        fail(errors, f"repository root cannot be determined: {exc.stderr.strip()}")

    for relative in sorted(REQUIRED_FILES):
        if not (root / relative).is_file():
            fail(errors, f"required file is missing: {relative}")
    for relative in [".github/workflows", "containers/m01", "config/m01", "docs/build", "docs/decisions", "docs/milestones", "manifests", "qa/golden", "qa/host/m01", "tools/m01"]:
        if not (root / relative).is_dir():
            fail(errors, f"required directory is missing: {relative}")

    try:
        tracked = run_git(root, "ls-files", "-z").stdout.split("\0")
        tracked = [path for path in tracked if path]
    except subprocess.CalledProcessError as exc:
        tracked = []
        fail(errors, f"cannot enumerate tracked files: {exc.stderr.strip()}")
    for path in tracked:
        lower = path.lower()
        if any(lower.endswith(suffix) for suffix in FORBIDDEN_SUFFIXES):
            fail(errors, f"forbidden binary/archive is tracked: {path}")
        if path.startswith("qa/results/"):
            fail(errors, f"generated M01 result is tracked: {path}")
        file_path = root / path
        if file_path.is_dir():
            continue
        try:
            data = file_path.read_bytes()
        except OSError as exc:
            fail(errors, f"cannot read tracked file {path}: {exc}")
            continue
        forbidden_literals = (
            b"/" + b"Users/",
            b"/" + b"private/tmp/",
            b"/" + b"private/var/",
            b"github" + b"_pat_",
        )
        if any(literal in data for literal in forbidden_literals):
            fail(errors, f"local path or credential-like value is tracked: {path}")

    template_path = root / "config/m01/fdkernel-nec98.mak"
    if template_path.is_file():
        if template_path.read_text(encoding="utf-8") != EXPECTED_FDKERNEL_TEMPLATE:
            fail(errors, "fdkernel M01 configuration template bytes are not exact")

    baseline_script = root / "tools/m01/build_baseline.sh"
    if baseline_script.is_file() and re.search(r"(?m)^\s*docker\s+exec(?:\s|$)", baseline_script.read_text(encoding="utf-8")):
        fail(errors, "M01 harness contains a forbidden docker exec command")

    if (root / "LICENSE").exists():
        fail(errors, "root LICENSE must remain absent while license selection is deferred")

    for path, (url, branch) in EXPECTED_SUBMODULES.items():
        try:
            actual_url = run_git(root, "config", "-f", ".gitmodules", f"submodule.{path}.url").stdout.strip()
            actual_branch = run_git(root, "config", "-f", ".gitmodules", f"submodule.{path}.branch").stdout.strip()
            assert_equal(errors, f".gitmodules URL for {path}", actual_url, url)
            assert_equal(errors, f".gitmodules branch for {path}", actual_branch, branch)
            stage = run_git(root, "ls-files", "--stage", "--", path).stdout.strip().split()
            if len(stage) < 2:
                fail(errors, f"submodule gitlink is missing: {path}")
            else:
                assert_equal(errors, f"gitlink mode for {path}", stage[0], "160000")
                assert_equal(errors, f"gitlink SHA for {path}", stage[1], expected_commits.get(path))
            head = run_git(root / path, "rev-parse", "HEAD").stdout.strip()
            assert_equal(errors, f"checked-out submodule SHA for {path}", head, expected_commits.get(path))
            status = run_git(root / path, "status", "--short", "--untracked-files=all").stdout
            if status:
                fail(errors, f"component is not clean: {path}: {status.strip()}")
        except subprocess.CalledProcessError as exc:
            fail(errors, f"submodule identity check failed for {path}: {exc.stderr.strip()}")

    contract_path = root / "manifests/m01-build-contract.json"
    lock_path = root / "manifests/toolchains.lock.json"
    try:
        contract = load_json(contract_path)
        lock = load_json(lock_path)
        assert_equal(errors, "contract schema_version", contract.get("schema_version"), 1)
        assert_equal(errors, "contract canonical_platform", contract.get("canonical_platform"), "linux/amd64")
        components = contract.get("components")
        if not isinstance(components, list) or len(components) != 3:
            fail(errors, "contract must contain exactly three components")
            components = []
        contract_commits = {component.get("path"): component.get("commit") for component in components}
        for path, commit in expected_commits.items():
            assert_equal(errors, f"contract commit for {path}", contract_commits.get(path), commit)
        for component in components:
            for artifact in component.get("required_artifacts", []):
                if artifact.get("namespace") not in {"fdkernel-nec98", "fdkernel-country", "freecom-nec98-japanese", "fdos-country"}:
                    fail(errors, f"unknown artifact namespace: {artifact.get('namespace')}")
            if component.get("upx_enabled") is not False:
                fail(errors, f"UPX is not disabled for {component.get('name')}")
        fdkernel = next((component for component in components if component.get("path") == "components/fdkernel"), None)
        actual_fdkernel_artifacts = [(item.get("namespace"), item.get("path")) for item in (fdkernel or {}).get("required_artifacts", [])]
        if actual_fdkernel_artifacts != EXPECTED_FDKERNEL_ARTIFACTS:
            fail(errors, f"fdkernel required artifact contract mismatch: {actual_fdkernel_artifacts!r}")
        commands = (fdkernel or {}).get("build_commands", [])
        expected_commands = [
            ["env", "-u", "XUPX", "-u", "UPXOPT", "make", "clobber", "COMPILER=owlinux"],
            ["env", "-u", "XUPX", "-u", "UPXOPT", "make", "all", "COMPILER=owlinux"],
        ]
        if commands != expected_commands:
            fail(errors, f"fdkernel build command contract mismatch: {commands!r}")
        freecom = next((component for component in components if component.get("path") == "components/freecom"), None)
        freecom_expected = {
            "commit": expected_commits["components/freecom"],
            "branch_metadata": "deterministic-build-timestamp",
            "base_commit": "c059aafe857f005b0d7d8295e3be67c0dba2aafd",
            "configuration_source": "components/freecom/config.std",
            "configuration_copy": ["cp", "/input/freecom-nec98.mak", "config.mak"],
            "timestamp_contract": "config/m01/freecom-build-timestamp.json",
        }
        for field, expected in freecom_expected.items():
            assert_equal(errors, f"FreeCOM contract {field}", (freecom or {}).get(field), expected)
        if (freecom or {}).get("build_commands") != [["./build.sh", "-r", "dbcs", "nec98", "watcom", "japanese"]]:
            fail(errors, f"FreeCOM build command contract mismatch: {(freecom or {}).get('build_commands')!r}")
        timestamp_contract = root / "config/m01/freecom-build-timestamp.json"
        if timestamp_contract.is_file():
            timestamp = load_json(timestamp_contract)
            for field, expected in EXPECTED_FREECOM_TIMESTAMP.items():
                assert_equal(errors, f"FreeCOM timestamp contract {field}", timestamp.get(field), expected)
        else:
            fail(errors, "FreeCOM timestamp contract is missing")
        assert_equal(errors, "toolchain lock schema_version", lock.get("schema_version"), 1)
        canonical = lock.get("canonical", {})
        base = canonical.get("base_image", {})
        assert_equal(errors, "locked base architecture", canonical.get("architecture"), "linux/amd64")
        assert_equal(errors, "locked amd64 manifest", base.get("amd64_manifest_digest"), "sha256:79676deb51ebb02885b0b9d33788e78a37cf1045ad79d1bb04c6a222c3556b3d")
        if lock.get("container_build_inputs", {}).get("required_upx") is not False:
            fail(errors, "toolchain lock must exclude UPX")
        open_watcom = canonical.get("open_watcom", {})
        for field in ("release", "release_tag", "release_id", "tag_commit", "package", "asset_id", "asset_size", "publisher_md5", "sha256", "official_upstream_url", "official_github_url", "verification_method", "archive_format", "install_path", "required_host_directory", "host_tools"):
            if field not in open_watcom:
                fail(errors, f"Open Watcom lock is missing {field}")
        assert_equal(errors, "Open Watcom release", open_watcom.get("release"), "Open Watcom 1.9")
        assert_equal(errors, "Open Watcom release tag", open_watcom.get("release_tag"), "ow1.9")
        if not isinstance(open_watcom.get("release_id"), int) or open_watcom.get("release_id") != 49559960:
            fail(errors, "Open Watcom release ID is not the locked 1.9 release")
        if not re.fullmatch(r"[0-9a-f]{40}", str(open_watcom.get("tag_commit", ""))):
            fail(errors, "Open Watcom tag commit is not a lowercase 40-hex ID")
        if not re.fullmatch(r"[0-9a-f]{64}", str(open_watcom.get("sha256", ""))):
            fail(errors, "Open Watcom archive SHA-256 is not a lowercase 64-hex value")
        assert_equal(errors, "Open Watcom package", open_watcom.get("package"), "open-watcom-c-linux-1.9")
        assert_equal(errors, "Open Watcom asset ID", open_watcom.get("asset_id"), 44807673)
        assert_equal(errors, "Open Watcom package size", open_watcom.get("asset_size"), 83959748)
        assert_equal(errors, "Open Watcom publisher MD5", open_watcom.get("publisher_md5"), "960fe6b5cf88769a42949f5fedf62827")
        assert_equal(errors, "Open Watcom package SHA-256", open_watcom.get("sha256"), "f7484be27eb70028010303fc16bb2acc5a785679567a568b940c28190ddbf3f3")
        assert_equal(errors, "Open Watcom upstream URL", open_watcom.get("official_upstream_url"), "https://openwatcom.org/ftp/install/open-watcom-c-linux-1.9")
        assert_equal(errors, "Open Watcom GitHub URL", open_watcom.get("official_github_url"), "https://github.com/open-watcom/open-watcom-1.9/releases/download/ow1.9/open-watcom-c-linux-1.9")
        assert_equal(errors, "Open Watcom archive format", open_watcom.get("archive_format"), "zip")
        assert_equal(errors, "Open Watcom install path", open_watcom.get("install_path"), "/opt/openwatcom-1.9")
        assert_equal(errors, "Open Watcom host directory", open_watcom.get("required_host_directory"), "binl")
        assert_equal(errors, "Open Watcom verification method", open_watcom.get("verification_method"), "dual-official-source-byte-identical-with-publisher-md5-and-sha256")
        if not isinstance(open_watcom.get("host_tools"), list) or [tool.get("name") for tool in open_watcom["host_tools"]] != ["wcc", "wcl", "wmake", "wlink", "wasm", "wlib"]:
            fail(errors, "Open Watcom host tool list is incomplete or out of order")
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        fail(errors, f"M01 manifest parsing failed: {exc}")

    results = root / "qa/results/m01"
    run1 = results / "run-1"
    run2 = results / "run-2"
    golden_path = root / "qa/golden/m01-baseline.json"
    comparison_path = results / "comparison.json"
    source_map_path = results / "runtime/source-archives.json"
    image_path = results / "runtime/image.json"
    download_path = results / "runtime/toolchain-download.json"
    image_tool_selection_path = results / "runtime/image-tool-selection.txt"
    image_probe_container_path = results / "runtime/image-probe-container.json"
    portability_audit_path = results / "runtime/host-portability-audit.json"
    freecom_timestamp_paths = [
        run1 / "tool-versions/freecom-timestamp.json",
        run2 / "tool-versions/freecom-timestamp.json",
    ]
    freecom_config_paths = [
        run1 / "tool-versions/freecom-watcomc.cfg",
        run2 / "tool-versions/freecom-watcomc.cfg",
    ]
    for path in [run1 / "manifest.json", run2 / "manifest.json", comparison_path, golden_path, source_map_path, image_path, download_path, image_tool_selection_path, image_probe_container_path, portability_audit_path, *freecom_timestamp_paths, *freecom_config_paths]:
        if not path.is_file():
            fail(errors, f"required M01 evidence is missing: {path.relative_to(root)}")
    try:
        if run1.is_dir() and run2.is_dir():
            if run_git(root, "check-ignore", "-q", "qa/results/m01/run-1/manifest.json", check=False).returncode != 0:
                fail(errors, "qa/results/m01 is not ignored")
        manifests = [load_json(run1 / "manifest.json"), load_json(run2 / "manifest.json")]
        comparison = load_json(comparison_path)
        golden = load_json(golden_path)
        source_map = load_json(source_map_path)
        image = load_json(image_path)
        download = load_json(download_path)
        image_probe_container = load_json(image_probe_container_path)
        portability_audit = load_json(portability_audit_path)
        for timestamp_path, config_path in zip(freecom_timestamp_paths, freecom_config_paths):
            timestamp_evidence = load_json(timestamp_path)
            for field, expected in EXPECTED_FREECOM_TIMESTAMP.items():
                assert_equal(errors, f"FreeCOM timestamp evidence {timestamp_path.parent.parent.name} {field}", timestamp_evidence.get(field), expected)
            assert_equal(errors, f"FreeCOM timestamp evidence {timestamp_path.parent.parent.name} ver_recompiled", timestamp_evidence.get("ver_recompiled"), True)
            assert_equal(errors, f"FreeCOM timestamp evidence {timestamp_path.parent.parent.name} wall-clock absence", timestamp_evidence.get("current_wall_clock_stamp_absent"), True)
            response_line = '-DFREECOM_BUILD_DATE="Feb 22 2025" -DFREECOM_BUILD_TIME="14:17:52"'
            if config_path.read_text(encoding="utf-8").count(response_line) != 1:
                fail(errors, f"FreeCOM response file does not contain exactly one deterministic timestamp line: {config_path.relative_to(root)}")
        assert_equal(errors, "host portability audit schema_version", portability_audit.get("schema_version"), 1)
        if not isinstance(portability_audit.get("records"), list):
            fail(errors, "host portability audit records are not a list")
        else:
            for record in portability_audit["records"]:
                if record.get("execution_class") not in {"host-executed", "container-executed", "data-text"}:
                    fail(errors, f"host portability audit has an unknown execution class: {record!r}")
        if not isinstance(portability_audit.get("corrections"), list) or len(portability_audit["corrections"]) < 2:
            fail(errors, "host portability audit corrections are incomplete")
        identity_pattern = re.compile(r"^sha256:[0-9a-f]{64}$")
        for label, value in (
            ("image resolved local config ID", image.get("resolved_local_image_config_id")),
            ("probe resolved local config ID", image_probe_container.get("resolved_local_image_config_id")),
            ("probe container runtime config ID", image_probe_container.get("container_runtime_image_config_id")),
        ):
            if not isinstance(value, str) or identity_pattern.fullmatch(value) is None:
                fail(errors, f"{label} is not a full lowercase SHA-256 identity")
        assert_equal(errors, "probe image config ID match", image_probe_container.get("image_config_id_match"), True)
        assert_equal(errors, "probe runtime config ID", image_probe_container.get("container_runtime_image_config_id"), image_probe_container.get("resolved_local_image_config_id"))
        assert_equal(errors, "probe Config.Image reference", image_probe_container.get("container_config_image_reference"), image_probe_container.get("image_reference"))
        assert_equal(errors, "comparison status", comparison.get("status"), "pass")
        assert_equal(errors, "comparison byte_identical", comparison.get("byte_identical"), True)
        assert_equal(errors, "golden comparison", golden.get("comparison"), "byte-identical")
        assert_equal(errors, "golden contract digest", golden.get("contract_sha256"), digest(contract_path))
        assert_equal(errors, "golden toolchain digest", golden.get("toolchain_lock_sha256"), digest(lock_path))
        if manifests[0].get("artifacts") != manifests[1].get("artifacts"):
            fail(errors, "run-1 and run-2 artifact manifests differ")
        if golden.get("artifacts") != manifests[0].get("artifacts"):
            fail(errors, "golden artifact manifest does not match run-1")
        if golden.get("source_archives") != manifests[0].get("source_archives"):
            fail(errors, "golden source archive map does not match run-1")
        if golden.get("informational_country_comparison") != comparison.get("informational_country_comparison"):
            fail(errors, "golden COUNTRY.SYS observation does not match comparison")
        locked_open_watcom = lock.get("canonical", {}).get("open_watcom", {})
        image_open_watcom = image.get("open_watcom", {})
        image_lock_fields = {
            "release": "release",
            "release_tag": "release_tag",
            "release_id": "release_id",
            "tag_commit": "tag_commit",
            "package": "package",
            "asset_id": "asset_id",
            "package_size": "asset_size",
            "publisher_md5": "publisher_md5",
            "package_sha256": "sha256",
            "official_upstream_url": "official_upstream_url",
            "official_github_url": "official_github_url",
            "verification_method": "verification_method",
        }
        for image_field, lock_field in image_lock_fields.items():
            assert_equal(errors, f"image Open Watcom {image_field}", image_open_watcom.get(image_field), locked_open_watcom.get(lock_field))
        assert_equal(errors, "image Open Watcom second-copy verification", image_open_watcom.get("verified_second_copy"), True)
        assert_equal(errors, "download Open Watcom release", download.get("release"), "Open Watcom 1.9")
        assert_equal(errors, "download Open Watcom package", download.get("package"), "open-watcom-c-linux-1.9")
        assert_equal(errors, "download Open Watcom first-copy deletion", download.get("first_download", {}).get("deleted"), True)
        assert_equal(errors, "download Open Watcom byte identity", download.get("byte_identical"), True)
        assert_equal(errors, "download Open Watcom second-copy verification", download.get("second_download", {}).get("verified"), True)
        assert_equal(errors, "download Open Watcom first URL", download.get("first_download", {}).get("source"), "official_upstream")
        assert_equal(errors, "download Open Watcom second URL", download.get("second_download", {}).get("source"), "official_github_release")
        assert_equal(errors, "download Open Watcom first size", download.get("first_download", {}).get("size"), locked_open_watcom.get("asset_size"))
        assert_equal(errors, "download Open Watcom second size", download.get("second_download", {}).get("size"), locked_open_watcom.get("asset_size"))
        assert_equal(errors, "download Open Watcom first MD5", download.get("first_download", {}).get("md5"), locked_open_watcom.get("publisher_md5"))
        assert_equal(errors, "download Open Watcom second MD5", download.get("second_download", {}).get("md5"), locked_open_watcom.get("publisher_md5"))
        assert_equal(errors, "download Open Watcom first SHA-256", download.get("first_download", {}).get("sha256"), locked_open_watcom.get("sha256"))
        assert_equal(errors, "download Open Watcom second SHA-256", download.get("second_download", {}).get("sha256"), locked_open_watcom.get("sha256"))
        assert_equal(errors, "image probe container command", image_probe_container.get("command_argv"), ["/bin/sh", "/input/image_tool_probe.sh"])
        assert_equal(errors, "image probe container platform", image_probe_container.get("requested_platform"), "linux/amd64")
        assert_equal(errors, "image probe container network", image_probe_container.get("network_mode"), "none")
        assert_equal(errors, "image probe container mounts", image_probe_container.get("mounts"), [])
        assert_equal(errors, "image probe container start status", image_probe_container.get("start_status"), 0)
        assert_equal(errors, "image probe container wait status", image_probe_container.get("wait_status"), 0)
        assert_equal(errors, "image probe container process status", image_probe_container.get("process_status"), 0)
        staged_script = image_probe_container.get("staged_script", {})
        staged_data = image_probe_container.get("staged_data", {})
        for label, staged in (("script", staged_script), ("data", staged_data)):
            staged_path = staged.get("path")
            if not isinstance(staged_path, str) or Path(staged_path).is_absolute() or ".." in Path(staged_path).parts:
                fail(errors, f"image probe staged {label} path is unsafe")
                continue
            staged_file = root / staged_path
            if not staged_file.is_file():
                fail(errors, f"image probe staged {label} file is missing: {staged_path}")
                continue
            assert_equal(errors, f"image probe staged {label} mode", format(staged_file.stat().st_mode & 0o777, "04o"), "0444")
            assert_equal(errors, f"image probe staged {label} size", staged.get("size"), staged_file.stat().st_size)
            assert_equal(errors, f"image probe staged {label} SHA-256", staged.get("sha256"), digest(staged_file))
        assert_equal(errors, "image probe staged script path", staged_script.get("path"), "qa/results/m01/runtime/image-probe-input/image_tool_probe.sh")
        assert_equal(errors, "image probe staged data path", staged_data.get("path"), "qa/results/m01/runtime/image-probe-input/image-tool-probe.env")
        tool_selection = image_tool_selection_path.read_text(encoding="utf-8")
        assert_equal(errors, "image tool selection WATCOM", "WATCOM=/opt/openwatcom-1.9" in tool_selection, True)
        assert_equal(errors, "image tool selection path", "/opt/openwatcom-1.9/binl" in tool_selection, True)
        for marker in (
            "wcc_sha256=d882c85922da81aa7956cc5ee5aacc3e2a85932ef346c424ce508ff499d1aba6",
            "wcl_sha256=47911ca4b28875d5d9157e9054a68e88180eedd08a5f66a82e1cd864e6f38ba3",
            "wmake_sha256=d13292a724fb000b51e719bf3a411c6870ab26e13b8e32855e88458a850de5b4",
            "wlink_sha256=e285c328f48b17e115cb6fd0f91f348a915adfd9eeb932eb3e7b4f3b50fc2838",
            "wasm_sha256=d4bc79eddea9afba5b6244203dd4ee4ef670161a099d0ea06f2a2943d4f23579",
            "wlib_sha256=0391b9363048520eb3e1da0712c42d096f9ef8407b2a450c2ae97b345a08ed84",
            "wcc_probe_status=0",
            "Open Watcom C16 Optimizing Compiler Version 1.9",
            "wmake_probe_status=0",
            "M01_WMAKE_PROBE_OK",
            "wmake_probe_output_match=true",
            "Open Watcom Make Version 1.9",
        ):
            if marker not in tool_selection:
                fail(errors, f"image tool-selection evidence lacks {marker}")
        for manifest in manifests:
            for record in manifest.get("artifacts", []):
                artifact = record.get("artifact", "")
                if Path(artifact).is_absolute() or ".." in Path(artifact).parts:
                    fail(errors, f"unsafe artifact path: {artifact}")
                path = run1 / "artifacts" / artifact if manifest is manifests[0] else run2 / "artifacts" / artifact
                if not path.is_file():
                    fail(errors, f"artifact file is missing: {path.relative_to(root)}")
                else:
                    assert_equal(errors, f"artifact size for {artifact}", path.stat().st_size, record.get("size"))
                    assert_equal(errors, f"artifact SHA-256 for {artifact}", digest(path), record.get("sha256"))
        for source_name, source_sha in source_map.items():
            source_file = results / "source" / f"{source_name}.tar"
            if not source_file.is_file():
                fail(errors, f"source archive is missing: {source_file.relative_to(root)}")
            else:
                assert_equal(errors, f"source archive SHA-256 for {source_name}", digest(source_file), source_sha)
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        fail(errors, f"M01 evidence parsing failed: {exc}")

    if errors:
        for message in errors:
            print(f"ERROR: {message}")
        raise SystemExit(1)
    print("M01 offline verification passed: structure, gitlinks, components, artifacts, golden manifest, and reproducibility evidence are valid")


if __name__ == "__main__":
    main()
