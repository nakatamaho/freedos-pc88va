#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Focused tests for the public M07R6 blocked status."""

from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("m07r6_verify", ROOT / "tools/m07/verify_m07r6.py")
assert SPEC and SPEC.loader
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class M07R6Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.status = VERIFY.load_canonical(ROOT / "config/m07/m07r6-public-status.json")
        self.schema = VERIFY.load_canonical(ROOT / "schema/m07r6-public-status.schema.json")

    def test_status_is_canonical_and_stops_at_s3(self) -> None:
        VERIFY.validate_schema(self.status, self.schema)
        VERIFY.validate_status(self.status)
        self.assertEqual(self.status["boundaries"]["last_reached"], "S2_MOTOR_STABLE")
        self.assertEqual(self.status["boundaries"]["first_blocked"], "S3_FDC_COMMAND")

    def test_request_consumer_is_independent_but_producer_is_not_promoted(self) -> None:
        self.assertTrue(self.status["predicate"]["consumer_independently_observed"])
        self.assertFalse(self.status["predicate"]["producer_fully_identified"])
        changed = copy.deepcopy(self.status)
        changed["predicate"]["producer_fully_identified"] = True
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.validate_status(changed)

    def test_s3_command_cannot_be_claimed(self) -> None:
        changed = copy.deepcopy(self.status)
        changed["observations"]["fdc_command"] = True
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.validate_status(changed)

    def test_m08_fields_remain_unresolved(self) -> None:
        changed = copy.deepcopy(self.status)
        changed["fields"]["unresolved"] = []
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.validate_status(changed)

    def test_public_private_boundary_rejects_path_and_concrete_value(self) -> None:
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.reject_public_text("/" + "Users" + "/example/private")
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.reject_public_text("physical_load_address: 0x1234")
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.reject_public_text("rom_sha256=synthetic")

    def test_historical_m07r5_and_component_pins_are_fixed(self) -> None:
        self.assertTrue(self.status["m07r5"]["historical_status_preserved"])
        self.assertTrue(self.status["m07r5"]["b2_evidence_consumed"])
        self.assertEqual(self.status["components"]["gitlinks"], VERIFY.COMPONENTS)

    def test_no_later_boundary_is_reported(self) -> None:
        self.assertFalse(self.status["observations"]["sector_transfer"])
        self.assertFalse(self.status["observations"]["fetch_correlated"])
        self.assertFalse(self.status["observations"]["marker"])


if __name__ == "__main__":
    unittest.main()
