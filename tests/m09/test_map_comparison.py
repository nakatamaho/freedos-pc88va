# SPDX-License-Identifier: GPL-2.0-or-later
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location(
    "compare_maps", Path(__file__).resolve().parents[2] / "tools/m09/compare_maps.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MapTests(unittest.TestCase):
    SOURCE = "Created on:       26/01/01 01:02:03\npublic_symbol\nLink time: 00:00.01\n"

    def test_only_timing_difference_allowed(self):
        MODULE.compare(self.SOURCE, self.SOURCE.replace("01:02:03", "02:03:04").replace("00:00.01", "00:00.02"))

    def test_symbol_difference_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.compare(self.SOURCE, self.SOURCE.replace("public_symbol", "other_symbol"))

    def test_missing_or_duplicate_field_rejected(self):
        for text in (self.SOURCE.replace("Link time:", "Elapsed:"), self.SOURCE + "Link time: 00:00.01\n"):
            with self.assertRaises(ValueError):
                MODULE.semantic_lines(text)

    def test_extra_diagnostic_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.compare(self.SOURCE, self.SOURCE + "unexpected diagnostic\n")
