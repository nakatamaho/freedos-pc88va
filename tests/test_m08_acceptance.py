# SPDX-License-Identifier: GPL-2.0-or-later
"""Public negative tests for the M08 acceptance-evidence gate."""

from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "m08_public_verify", ROOT / "tools/m08/verify_m08_public.py"
)
assert SPEC and SPEC.loader
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class M08AcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(
            (ROOT / "config/m08/loader-contract.json").read_text(encoding="utf-8")
        )

    def test_accepted_contract_requires_artifact_manifest(self) -> None:
        changed = copy.deepcopy(self.contract)
        del changed["public_artifact_manifest"]
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.validate_acceptance_evidence(changed)

    def test_accepted_contract_requires_golden(self) -> None:
        changed = copy.deepcopy(self.contract)
        del changed["public_golden"]
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.validate_acceptance_evidence(changed)

    def test_accepted_contract_requires_vaeg_identity(self) -> None:
        changed = copy.deepcopy(self.contract)
        del changed["vaeg_qualification"]
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.validate_acceptance_evidence(changed)

    def test_accepted_contract_rejects_manifest_digest_drift(self) -> None:
        changed = copy.deepcopy(self.contract)
        changed["public_artifact_manifest"]["sha256"] = "0" * 64
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.validate_acceptance_evidence(changed)

    def test_accepted_contract_requires_two_run_evidence(self) -> None:
        qualification = ROOT / "config/m08/vaeg-qualification.json"
        original = json.loads(qualification.read_text(encoding="utf-8"))
        original["qualification"]["fresh_clean_runs"] = 1
        original["qualification"]["canonical_projection"] = "different"
        real_json = VERIFY._json

        def altered(path: Path) -> dict:
            value = real_json(path)
            return original if path == qualification else value

        with mock.patch.object(VERIFY, "_json", side_effect=altered):
            with self.assertRaises(VERIFY.VerificationError):
                VERIFY.validate_acceptance_evidence(self.contract)


if __name__ == "__main__":
    unittest.main()
