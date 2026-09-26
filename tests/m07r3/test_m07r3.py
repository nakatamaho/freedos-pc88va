#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Focused public tests for the M07R3 unresolved-control record."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("m07r3_verify", ROOT / "tools/m07r3/verify_m07r3.py")
assert SPEC and SPEC.loader
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class M07R3Tests(unittest.TestCase):
    def test_public_status_is_canonical_and_unresolved(self) -> None:
        data = VERIFY.load_json(ROOT / "config/m07/m07r3-public-status.json")
        VERIFY.validate_status(data)
        self.assertEqual(data["comparison"]["last_common_boundary"], "B1")
        self.assertEqual(data["m08"]["mandatory_resolved_count"], 0)

    def test_private_path_marker_is_rejected(self) -> None:
        with self.assertRaises(VERIFY.M07R3Error):
            VERIFY.reject_private_text("/" + "Users" + "/example/private")

    def test_private_concrete_fields_are_rejected(self) -> None:
        with self.assertRaises(VERIFY.M07R3Error):
            VERIFY.reject_private_text("winning_variant=synthetic")

    def test_positive_control_cannot_be_claimed_by_this_record(self) -> None:
        data = json.loads((ROOT / "config/m07/m07r3-public-status.json").read_text())
        self.assertFalse(data["m07r2"]["resumed"])
        self.assertEqual(data["classification"], "U")

    def test_components_are_fixed(self) -> None:
        data = json.loads((ROOT / "config/m07/m07r3-public-status.json").read_text())
        self.assertEqual(data["components"]["gitlinks"], VERIFY.COMPONENTS)


if __name__ == "__main__":
    unittest.main()
