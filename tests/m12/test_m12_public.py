#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class M12PublicTests(unittest.TestCase):
    def test_contract_and_schema_are_actual_instances(self):
        import sys
        sys.path.insert(0, str(ROOT / "tools/m12"))
        import verify_m12
        verify_m12.content(ROOT)

    def test_resident_source_is_not_loader_only(self):
        source = (ROOT / "components/fdkernel/pc88va/kernel/resident_disk.asm").read_text()
        self.assertIn("pc88va_kernel_disk_read_:", source)
        self.assertIn("pc88va_m12_diagnostic_:", source)
        self.assertIn("call pc88va_disk_read_core", source)
        self.assertNotIn("pc88va_loader_handoff_core", source)

    def test_fixture_is_read_only_and_distinct(self):
        source = (ROOT / "tools/m12/build_media.py").read_text()
        self.assertIn("FIXTURE_LBAS = (200, 201)", source)
        self.assertIn('"read_only": True', source)
        self.assertNotIn("fdd_write", source)


if __name__ == "__main__":
    unittest.main()
