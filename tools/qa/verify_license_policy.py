#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Verify the M04R1 root-license policy without network access."""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path


SPDX_EXPRESSION = "GPL-2.0-or-later"
M04_START_COMMIT = "f099b8ec1ca7edfdef3619ddea59369b44e49014"
COPYING_SHA256 = "0f1e68d9b4a580cdcca4c5f4e3b8046f7a8759da05edd109cff081bc484b3c4b"
EXPECTED_GITLINKS = {
    "components/fdkernel": "6523acdb87f4665e6068ea331859885267242005",
    "components/freecom": "855281a3114b43ad4b8d9a320f2aca39be046bba",
    "components/country": "23f189cca3420606eae8723884fa92ccd65eb307",
}
PROTECTED_M04_IDENTITIES = {
    "config/contracts/m04-provisional-pc88va-boot-media.json":
        "f2e4efdc9d9e3a31dc100b81896427beeaeaca29d36d692b5dfeb5fb459460f4",
    "config/contracts/m04-provisional-pc88va-boot-media.schema.json":
        "f50c099211e2e70f959fb1cc70e93553699f9862113b50c7cda7f29816e6b7c0",
    "config/contracts/m04-evidence-matrix.json":
        "0612699d305738f2db131cb87c5fa7e9393b206672d6bec27483a602e7e91770",
}
FORBIDDEN_TRACKED_SUFFIXES = {
    ".rom", ".d88", ".d98", ".hdi", ".hdd", ".img", ".ima", ".iso",
    ".o", ".obj", ".exe", ".com", ".sys", ".tar", ".zip", ".log",
}
NOTICE_FRAGMENTS = (
    "Original source code, build scripts, tests, and documentation contributed",
    "where the project contributors have the right to license that material",
    "complete unmodified GNU General Public License version 2 text is in",
    "WITHOUT ANY WARRANTY",
    "Files carrying their own copyright or license notices remain governed by",
    "Git submodules are independent works and retain their upstream licenses.",
    "Generated bundles can contain independently licensed component outputs.",
    "Private manuals, Tekumani material, ROM images, PC-Engine D88 images, and",
    "are not part of the public repository or this public",
    "No trademark permission for FreeDOS, NEC, PC-88VA",
)
GPL_MARKERS = (
    b"GNU GENERAL PUBLIC LICENSE",
    b"Version 2, June 1991",
    b"  9. The Free Software Foundation may publish revised and/or new versions",
    b'specifies a version number of this License which applies to it and "any\n',
    b"either of that version or of any later version published by the Free",
    b"END OF TERMS AND CONDITIONS",
)


class VerificationError(RuntimeError):
    """Raised when the root-license contract is not satisfied."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_regular_file(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise VerificationError(f"required regular file is missing or unsafe: {path.name}")
    return path.read_bytes()


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ("git", *args), cwd=root, check=False, capture_output=True, text=True
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise VerificationError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def verify_copying(root: Path) -> str:
    source = read_regular_file(root / "components/fdkernel/COPYING")
    copying = read_regular_file(root / "COPYING")
    source_digest = sha256_bytes(source)
    if source_digest != COPYING_SHA256:
        raise VerificationError("pinned fdkernel COPYING identity does not match M04R1 provenance")
    if copying != source:
        raise VerificationError("root COPYING is not byte-identical to pinned fdkernel COPYING")
    if sha256_bytes(copying) != COPYING_SHA256:
        raise VerificationError("root COPYING SHA-256 does not match the accepted GPLv2 text")
    for marker in GPL_MARKERS:
        if marker not in copying:
            raise VerificationError(f"root COPYING is missing GPLv2 marker: {marker!r}")
    if not copying.endswith(b"\n"):
        raise VerificationError("root COPYING must end with one newline")
    return source_digest


def verify_notice(root: Path) -> None:
    raw = read_regular_file(root / "LICENSE.md")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VerificationError("LICENSE.md is not UTF-8") from exc
    normalized = " ".join(text.split())
    if SPDX_EXPRESSION not in normalized:
        raise VerificationError(f"LICENSE.md does not contain exact SPDX expression {SPDX_EXPRESSION}")
    for forbidden in ("GPL-2.0-only", "GPL-2.0+", "GPLv2"):
        if forbidden in normalized:
            raise VerificationError(f"LICENSE.md contains ambiguous or incorrect root identifier: {forbidden}")
    for fragment in NOTICE_FRAGMENTS:
        if fragment not in normalized:
            raise VerificationError(f"LICENSE.md is missing required policy text: {fragment}")
    if "does not relicense or sublicense them" not in normalized:
        raise VerificationError("LICENSE.md does not preserve independent submodule licensing")


def verify_current_documentation(root: Path) -> None:
    policy = read_regular_file(root / "docs/licensing/README.md").decode("utf-8")
    required = (
        "Root license: GPL-2.0-or-later",
        "Decision milestone: M04R1",
        "M04R1 supersedes the earlier deferred root-license status.",
        "SPDX-License-Identifier: GPL-2.0-or-later",
    )
    for fragment in required:
        if fragment not in policy:
            raise VerificationError(f"current licensing documentation is missing: {fragment}")
    manifest = read_regular_file(root / "manifests/licenses.yml").decode("utf-8")
    for line in (
        "status: decided",
        "parent_license: GPL-2.0-or-later",
        "parent_full_text: COPYING",
        "parent_notice: LICENSE.md",
        "decision_milestone: M04R1",
    ):
        if not re.search(rf"(?m)^{re.escape(line)}$", manifest):
            raise VerificationError(f"license manifest is missing exact line: {line}")


def verify_m04_identities(root: Path) -> None:
    for relative, expected in PROTECTED_M04_IDENTITIES.items():
        actual = sha256_bytes(read_regular_file(root / relative))
        if actual != expected:
            raise VerificationError(f"protected M04 identity changed: {relative}: {actual}")
    result = subprocess.run(
        ("git", "merge-base", "--is-ancestor", M04_START_COMMIT, "HEAD"),
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise VerificationError("accepted M04 commit is not an ancestor of HEAD")


def verify_components(root: Path) -> None:
    for relative, expected in EXPECTED_GITLINKS.items():
        fields = run_git(root, "ls-files", "--stage", "--", relative).strip().split()
        if len(fields) < 4 or fields[0] != "160000" or fields[1] != expected:
            actual = fields[1] if len(fields) >= 2 else "missing"
            raise VerificationError(f"component gitlink mismatch: {relative}: {actual}")
        head = run_git(root, "-C", relative, "rev-parse", "HEAD").strip()
        if head != expected:
            raise VerificationError(f"component worktree HEAD mismatch: {relative}: {head}")
        status = run_git(
            root, "-C", relative, "status", "--short", "--untracked-files=all"
        )
        if status:
            raise VerificationError(f"component worktree is dirty: {relative}")


def verify_tracked_safety(root: Path) -> None:
    tracked = [item for item in run_git(root, "ls-files", "-z").split("\0") if item]
    forbidden = []
    for relative in tracked:
        lower = relative.lower()
        suffix = Path(lower).suffix
        if suffix in FORBIDDEN_TRACKED_SUFFIXES:
            forbidden.append(relative)
        if lower.startswith(("private/", "local/", "qa/results/")):
            forbidden.append(relative)
        if "pc88va-private-docs" in lower or "private-evidence" in lower:
            forbidden.append(relative)
    if forbidden:
        raise VerificationError("forbidden tracked private or generated files: " + ", ".join(sorted(set(forbidden))))


def verify_repository(root: Path) -> str:
    digest = verify_copying(root)
    verify_notice(root)
    verify_current_documentation(root)
    verify_m04_identities(root)
    verify_components(root)
    verify_tracked_safety(root)
    return digest


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    try:
        digest = verify_repository(root)
    except (OSError, UnicodeDecodeError, VerificationError) as exc:
        print(f"M04R1 license verification failed: {exc}", file=sys.stderr)
        return 1
    print(f"M04R1 LICENSE POLICY PASS: {SPDX_EXPRESSION}; COPYING sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
