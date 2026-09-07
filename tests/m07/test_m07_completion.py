#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Focused tests for the privacy-safe M07 completion record."""

from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "m07_completion_verify", ROOT / "tools/m07/verify_m07_completion.py"
)
assert SPEC and SPEC.loader
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class M07CompletionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.status = VERIFY.load_canonical(
            ROOT / "config/m07/m07-completion-public-status.json"
        )
        self.schema = VERIFY.load_canonical(
            ROOT / "schema/m07-completion-public-status.schema.json"
        )

    def test_completion_record_is_canonical_and_valid(self) -> None:
        VERIFY.validate_schema(self.status, self.schema)
        VERIFY.validate_status(self.status)

    def test_all_consumer_and_transfer_boundaries_are_required(self) -> None:
        changed = copy.deepcopy(self.status)
        changed["boundaries"]["g_reached"].remove("G8_REQUEST_CONSUMED")
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.validate_status(changed)
        changed = copy.deepcopy(self.status)
        changed["boundaries"]["h_reached"].remove("H7_SECTOR_DATA_COMMITTED")
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.validate_status(changed)

    def test_all_eight_fields_are_private_and_resolved(self) -> None:
        self.assertEqual(self.status["fields"]["resolved_count"], 8)
        self.assertEqual(
            [item["id"] for item in self.status["fields"]["items"]], VERIFY.FIELDS
        )
        changed = copy.deepcopy(self.status)
        changed["fields"]["items"][0]["publication_state"] = "public"
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.validate_status(changed)

    def test_private_gate_requires_two_run_pairs_and_preserved_inputs(self) -> None:
        changed = copy.deepcopy(self.status)
        changed["private_gate"]["projection_determinism"] = "different"
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.validate_status(changed)
        changed = copy.deepcopy(self.status)
        changed["private_gate"]["input_preservation"] = "failed"
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.validate_status(changed)

    def test_vaeg_commit_ci_and_trace_identities_are_fixed(self) -> None:
        changed = copy.deepcopy(self.status)
        changed["vaeg"]["final_commit"] = "0" * 40
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.validate_status(changed)
        changed = copy.deepcopy(self.status)
        changed["vaeg"]["accepted_ci_conclusion"] = "pending"
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.validate_status(changed)

    def test_hardware_and_m08_are_not_started(self) -> None:
        changed = copy.deepcopy(self.status)
        changed["validation"]["hardware"] = "pass"
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.validate_status(changed)
        changed = copy.deepcopy(self.status)
        changed["validation"]["m08"] = "started"
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.validate_status(changed)

    def test_public_output_rejects_private_paths_and_concrete_values(self) -> None:
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.reject_public_text("/" + "Users" + "/example/private")
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.reject_public_text("physical_load_address=0x1234")
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.reject_public_text("rom_sha256=synthetic")

    def test_component_gitlinks_are_fixed(self) -> None:
        changed = copy.deepcopy(self.status)
        changed["components"]["gitlinks"]["components/fdkernel"] = "0" * 40
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.validate_status(changed)


if __name__ == "__main__":
    unittest.main()
