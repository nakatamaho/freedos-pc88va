# SPDX-License-Identifier: GPL-2.0-or-later
"""Focused positive and negative tests for the M04R1 license policy."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
from tools.qa import verify_license_policy as verifier  # noqa: E402


class LicensePolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        source = (REPO_ROOT / "components/fdkernel/COPYING").read_bytes()
        (self.root / "components/fdkernel").mkdir(parents=True)
        (self.root / "components/fdkernel/COPYING").write_bytes(source)
        (self.root / "COPYING").write_bytes(source)
        (self.root / "LICENSE.md").write_bytes((REPO_ROOT / "LICENSE.md").read_bytes())

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_complete_copying_and_notice_are_accepted(self) -> None:
        self.assertEqual(verifier.verify_copying(self.root), verifier.COPYING_SHA256)
        verifier.verify_notice(self.root)

    def test_gpl_2_only_is_rejected(self) -> None:
        path = self.root / "LICENSE.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace("GPL-2.0-or-later", "GPL-2.0-only"),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(verifier.VerificationError, "exact SPDX expression"):
            verifier.verify_notice(self.root)

    def test_missing_copying_is_rejected(self) -> None:
        (self.root / "COPYING").unlink()
        with self.assertRaisesRegex(verifier.VerificationError, "missing or unsafe"):
            verifier.verify_copying(self.root)

    def test_truncated_copying_is_rejected(self) -> None:
        (self.root / "COPYING").write_bytes(b"GNU GENERAL PUBLIC LICENSE\nVersion 2\n")
        with self.assertRaisesRegex(verifier.VerificationError, "not byte-identical"):
            verifier.verify_copying(self.root)

    def test_missing_submodule_preservation_is_rejected(self) -> None:
        path = self.root / "LICENSE.md"
        text = path.read_text(encoding="utf-8").replace(
            "Git submodules are independent works and retain their upstream licenses.",
            "Git submodules are covered by the parent license.",
        )
        path.write_text(text, encoding="utf-8")
        with self.assertRaisesRegex(verifier.VerificationError, "required policy text"):
            verifier.verify_notice(self.root)

    def test_private_material_inclusion_is_rejected(self) -> None:
        path = self.root / "LICENSE.md"
        text = path.read_text(encoding="utf-8").replace(
            "are not part of the public repository or this public",
            "are part of the public repository and this public",
        )
        path.write_text(text, encoding="utf-8")
        with self.assertRaisesRegex(verifier.VerificationError, "required policy text"):
            verifier.verify_notice(self.root)

    def test_checked_out_repository_policy(self) -> None:
        self.assertEqual(verifier.verify_repository(REPO_ROOT), verifier.COPYING_SHA256)


if __name__ == "__main__":
    unittest.main()
