#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Resolve the current component identity without rewriting historical locks."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path


M06_LOCK = Path("manifests/m06-components.lock.json")
HISTORICAL_LOCK = Path("manifests/components.lock.json")
HISTORICAL_LOCK_SHA256 = "440e481b28c740875489a6953a246ce5370c44074053c7aad3f80e79ec40c19c"
EXPECTED_PATHS = {
    "components/country",
    "components/fdkernel",
    "components/freecom",
}
EXPECTED_POLICY = {
    "components/country": ("country", "https://github.com/FDOS/country.git", "master"),
    "components/fdkernel": ("fdkernel", "https://github.com/nakatamaho/fdkernel.git", "necpc88va"),
    "components/freecom": ("freecom", "https://github.com/nakatamaho/freecom_dbcs2.git", "deterministic-build-timestamp"),
}
HEX40 = re.compile(r"[0-9a-f]{40}")
HEX64 = re.compile(r"[0-9a-f]{64}")


class CurrentComponentError(RuntimeError):
    """Raised when the M06 current-component overlay is not exact."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_canonical_json(path: Path) -> dict:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CurrentComponentError(f"cannot parse current component lock: {exc}") from exc
    canonical = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")
    if raw != canonical:
        raise CurrentComponentError("current component lock is not canonical JSON")
    return value


def resolve_current_components(root: Path, historical: dict[str, str]) -> dict[str, str]:
    """Return current gitlink expectations after validating the M06 overlay."""
    root = root.resolve()
    if set(historical) != EXPECTED_PATHS:
        raise CurrentComponentError("historical component path set is invalid")
    lock_path = root / M06_LOCK
    if not lock_path.exists():
        return dict(historical)
    if _sha256(root / HISTORICAL_LOCK) != HISTORICAL_LOCK_SHA256:
        raise CurrentComponentError("historical component lock identity changed")
    data = _load_canonical_json(lock_path)
    if data.get("schema_version") != 1 or data.get("status") not in ("current-m06", "current-m08"):
        raise CurrentComponentError("current component lock schema or status is invalid")
    historical_record = data.get("historical_components_lock")
    if historical_record != {"path": HISTORICAL_LOCK.as_posix(), "sha256": HISTORICAL_LOCK_SHA256}:
        raise CurrentComponentError("current lock does not preserve the historical lock identity")
    components = data.get("components")
    if not isinstance(components, list) or len(components) != 3:
        raise CurrentComponentError("current component lock must contain exactly three components")
    by_path = {}
    for item in components:
        if not isinstance(item, dict) or item.get("path") in by_path:
            raise CurrentComponentError("current component lock contains an invalid or duplicate entry")
        by_path[item.get("path")] = item
    if set(by_path) != EXPECTED_PATHS:
        raise CurrentComponentError("current component lock path set is invalid")
    current = {}
    for path in sorted(EXPECTED_PATHS):
        expected_name, expected_repository, expected_branch = EXPECTED_POLICY[path]
        if path == "components/fdkernel" and data.get("status") == "current-m08":
            expected_branch = "topic/m08-pc88va-disk-loader-handoff"
        if (
            by_path[path].get("name") != expected_name
            or by_path[path].get("repository") != expected_repository
            or by_path[path].get("branch") != expected_branch
        ):
            raise CurrentComponentError(f"current component provenance policy is invalid: {path}")
        commit = by_path[path].get("commit")
        if not isinstance(commit, str) or HEX40.fullmatch(commit) is None:
            raise CurrentComponentError(f"current component commit is invalid: {path}")
        current[path] = commit
    for path in ("components/freecom", "components/country"):
        if current[path] != historical[path] or by_path[path].get("parent_commit") is not None:
            raise CurrentComponentError(f"M06 unexpectedly changes {path}")
    fdkernel = by_path["components/fdkernel"]
    archive = fdkernel.get("source_archive_sha256")
    if (
        fdkernel.get("parent_commit") != historical["components/fdkernel"]
        or fdkernel.get("branch") not in ("necpc88va", "topic/m08-pc88va-disk-loader-handoff")
        or not isinstance(archive, str)
        or HEX64.fullmatch(archive) is None
    ):
        raise CurrentComponentError("M06 fdkernel lineage or archive identity is invalid")
    result = subprocess.run(
        ("git", "merge-base", "--is-ancestor", historical["components/fdkernel"], current["components/fdkernel"]),
        cwd=root / "components/fdkernel",
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode:
        raise CurrentComponentError("M06 fdkernel commit is not a descendant of the historical commit")
    return current
