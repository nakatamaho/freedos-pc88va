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

    def test_schema_digest_drift_is_rejected(self) -> None:
        with mock.patch.object(VERIFY, "ARTIFACT_SCHEMA_SHA256", "0" * 64):
            with self.assertRaisesRegex(VERIFY.VerificationError, "schema is missing or differs"):
                VERIFY.validate_acceptance_evidence(self.contract)

    def test_m05_descendant_evidence_paths_remain_narrow(self) -> None:
        import sys
        sys.path.insert(0, str(ROOT / "tools/m05"))
        import verify_m05
        verify_m05.validate_descendant_paths([
            "qa/golden/m08-artifact-manifest.json", "qa/golden/m08-golden.json",
            "docs/porting/m08r2-report.md"])
        for path in ("qa/golden/m08-unreviewed.json", "docs/porting/m08r2-unreviewed.md"):
            with self.assertRaises(verify_m05.ValidationError):
                verify_m05.validate_descendant_paths([path])


class M08ArtifactSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = json.loads(VERIFY.ARTIFACT_MANIFEST_PATH.read_text())
        self.schema = json.loads(VERIFY.ARTIFACT_SCHEMA_PATH.read_text())

    def reject(self) -> None:
        with self.assertRaisesRegex(VERIFY.VerificationError, "schema conformance"):
            VERIFY.validate_artifact_schema(self.data, self.schema)

    def test_accepted_manifest_conforms(self) -> None:
        VERIFY.validate_artifact_schema(self.data, self.schema)

    def test_kernel_fields_are_required(self) -> None:
        for field in ("format", "size", "sha256", "compile_manifest_sha256",
                      "kernel_interface_sha256", "symbol_evidence_sha256"):
            with self.subTest(field=field):
                value = self.data["artifacts"]["kernel_sys"].pop(field)
                self.reject()
                self.data["artifacts"]["kernel_sys"][field] = value

    def test_kernel_unknown_field_rejected(self) -> None:
        self.data["artifacts"]["kernel_sys"]["unregistered"] = True
        self.reject()

    def test_kernel_digest_type_and_pattern(self) -> None:
        for field in ("sha256", "compile_manifest_sha256", "kernel_interface_sha256",
                      "symbol_evidence_sha256"):
            original = self.data["artifacts"]["kernel_sys"][field]
            for value in (None, 123, "a" * 63, "g" * 64, "A" * 64):
                with self.subTest(field=field, value=value):
                    self.data["artifacts"]["kernel_sys"][field] = value
                    self.reject()
            self.data["artifacts"]["kernel_sys"][field] = original

    def test_generic_artifacts_reject_kernel_fields(self) -> None:
        for name in ("loader_stage1", "loader_stage2", "raw_media", "d88_media"):
            with self.subTest(artifact=name):
                self.data["artifacts"][name]["compile_manifest_sha256"] = "a" * 64
                self.reject()
                del self.data["artifacts"][name]["compile_manifest_sha256"]

    def test_invalid_schema_rejected(self) -> None:
        self.schema["$defs"]["kernel_artifact"]["type"] = "not-a-json-type"
        self.reject()

    def test_acceptance_verifier_calls_schema_validation(self) -> None:
        original_json = VERIFY._json
        self.data["artifacts"]["kernel_sys"]["extra"] = 1
        def altered(path):
            return self.data if path == VERIFY.ARTIFACT_MANIFEST_PATH else original_json(path)
        with mock.patch.object(VERIFY, "_json", side_effect=altered):
            with self.assertRaisesRegex(VERIFY.VerificationError, "schema conformance"):
                VERIFY.validate_acceptance_evidence(json.loads(VERIFY.CONTRACT_PATH.read_text()))


if __name__ == "__main__":
    unittest.main()
