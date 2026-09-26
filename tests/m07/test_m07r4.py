#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Focused tests for the public M07R4 redacted status."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("m07r4_verify", ROOT / "tools/m07/verify_m07r4.py")
assert SPEC and SPEC.loader
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class M07R4Tests(unittest.TestCase):
    def test_public_status_is_canonical_and_b2_blocked(self) -> None:
        data = VERIFY.load_canonical(ROOT / "config/m07/m07r4-public-status.json")
        VERIFY.validate_schema(data, VERIFY.load_canonical(ROOT / "schema/m07r4-public-status.schema.json"))
        VERIFY.validate_status(data)
        self.assertEqual(data["boundaries"]["first_unobserved"], "B2")
        self.assertEqual(data["fields"]["resolved_count"], 0)

    def test_unknown_field_requires_the_complete_unresolved_set(self) -> None:
        data = json.loads((ROOT / "config/m07/m07r4-public-status.json").read_text())
        data["fields"]["unresolved"] = []
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.validate_status(data)

    def test_private_path_and_private_value_markers_are_rejected(self) -> None:
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.reject_public_text("/" + "Users" + "/example/private")
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY.reject_public_text("winning_variant=synthetic")

    def test_private_values_are_redacted(self) -> None:
        data = json.loads((ROOT / "config/m07/m07r4-public-status.json").read_text())
        self.assertFalse(data["private_gate"]["concrete_values_published"])
        self.assertEqual(data["fields"]["resolved"], [])

    def test_components_are_fixed(self) -> None:
        data = json.loads((ROOT / "config/m07/m07r4-public-status.json").read_text())
        self.assertEqual(data["components"]["gitlinks"], VERIFY.COMPONENTS)


if __name__ == "__main__":
    unittest.main()
