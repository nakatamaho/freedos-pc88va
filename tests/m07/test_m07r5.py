#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Focused tests for the public M07R5 blocked status."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("m07r5_verify", ROOT / "tools/m07/verify_m07r5.py")
assert SPEC and SPEC.loader
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class M07R5Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.status = VERIFY.load_canonical(ROOT / "config/m07/m07r5-public-status.json")
        self.schema = VERIFY.load_canonical(ROOT / "schema/m07r5-public-status.schema.json")

    def test_public_status_is_canonical_and_b2_reached(self) -> None:
        VERIFY.validate_schema(self.status, self.schema)
        VERIFY.validate_status(self.status)
        self.assertEqual(self.status["boundaries"]["last_reached"], "B2")
        self.assertEqual(self.status["boundaries"]["first_blocked"], "B3")

    def test_m08_fields_remain_unresolved(self) -> None:
        changed = json.loads(json.dumps(self.status))
        changed["fields"]["unresolved"] = []
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.validate_status(changed)

    def test_producer_cannot_be_marked_identified(self) -> None:
        changed = json.loads(json.dumps(self.status))
        changed["predicate"]["producer_fully_identified"] = True
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.validate_status(changed)

    def test_private_path_and_concrete_value_are_rejected(self) -> None:
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.reject_public_text("/" + "Users" + "/example/private")
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.reject_public_text("physical_load_address: 0x1234")
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.reject_public_text("rom_sha256=synthetic")

    def test_old_no_request_record_is_not_current_evidence(self) -> None:
        self.assertFalse(self.status["supersedes"]["historical_no_request_admissible"])
        self.assertTrue(self.status["observations"]["main_subsystem_request"])

    def test_component_pins_are_fixed(self) -> None:
        self.assertEqual(self.status["components"]["gitlinks"], VERIFY.COMPONENTS)


if __name__ == "__main__":
    unittest.main()
