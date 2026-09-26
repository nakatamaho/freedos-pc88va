#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""ROM-free public checks for the M14 DOS workflow fixtures."""

from __future__ import annotations

import subprocess
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/m14/fixtures"
MODULE_SPEC = importlib.util.spec_from_file_location("m14_block_check", ROOT / "tools/m14/check_block_probe.py")
BLOCK = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(BLOCK)
from build_media import build_d88  # noqa: E402


class M14FixtureTests(unittest.TestCase):
    def test_block_checker_accepts_exact_patterns_and_exact_restoration(self):
        spec = json.loads((ROOT / "config/m05/media.json").read_text())
        raw = bytes(spec["geometry"]["total_bytes"])
        before = build_d88(spec, raw)
        changed = bytearray(raw)
        bps = spec["geometry"]["bytes_per_sector"]
        for lba, count in BLOCK.cases(spec):
            changed[lba*bps:(lba+count)*bps] = BLOCK.pattern(lba, count, bps)
        after = build_d88(spec, bytes(changed))
        result = BLOCK.check(before, after, spec, False)
        self.assertEqual(result["changed_lbas"], result["target_lbas"])
        self.assertTrue(result["metadata_unchanged"])
        self.assertEqual(BLOCK.check(before, before, spec, True)["changed_bytes"], 0)
        for lba in (0, 3):
            corrupt = bytearray(changed)
            corrupt[lba*bps+23] ^= 1
            with self.subTest(lba=lba), self.assertRaises(ValueError):
                BLOCK.check(before, build_d88(spec, bytes(corrupt)), spec, False)
        with self.assertRaises(ValueError):
            BLOCK.check(before, after, spec, True)
        with self.assertRaises(ValueError):
            BLOCK.check(before, before, spec, False)
        for offset in (0x1a, 0x20, 688+14):
            corrupt = bytearray(after)
            corrupt[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                BLOCK.check(before, bytes(corrupt), spec, False)

    def test_block_probe_is_pre_dos_and_links_production_objects(self):
        source = (FIXTURES / "m14_block_boot.asm").read_text()
        builder = (ROOT / "tools/m14/build_block_probe.sh").read_text()
        self.assertNotIn("int 21h", source)
        self.assertNotIn("int 25h", source)
        self.assertIn("call pc88va_machine_init_", source)
        for name in ("m13_platform", "resident_disk", "machine_services"):
            self.assertIn(name, builder)
        self.assertIn("FL_VERIFY", source)
        self.assertIn("m14_block_stop:", source)

    def test_sources_cover_the_required_dos_services(self):
        source = (FIXTURES / "m14_file_probe.asm").read_text(encoding="utf-8")
        for function in ("3ch", "3dh", "3eh", "3fh", "40h", "41h", "42h", "56h", "39h", "3ah"):
            self.assertIn(f"mov ah, {function}", source)
        self.assertIn("xor cx, cx", source)
        self.assertIn("M14FILE:PASS", source)

    def test_fixture_sources_build_byte_identically(self):
        if shutil.which("nasm") is None:
            self.skipTest("NASM is not installed on this host")
        with tempfile.TemporaryDirectory(prefix="m14-fixtures-") as directory:
            output = Path(directory)
            for name in ("m14_file_probe", "m14_full_probe", "m14_swap_probe", "m14_io_probe", "m14_read_probe"):
                source = FIXTURES / f"{name}.asm"
                self.assertIn("cpu 8086", source.read_text(), name)
                first = output / f"{name}-1.com"
                second = output / f"{name}-2.com"
                for target in (first, second):
                    result = subprocess.run(["nasm", "-f", "bin", "-o", str(target), str(source)],
                                            capture_output=True)
                    self.assertEqual(result.returncode, 0,
                                     result.stderr.decode(errors="replace"))
                self.assertEqual(first.read_bytes(), second.read_bytes(), name)
                self.assertLess(len(first.read_bytes()), 65536, name)


if __name__ == "__main__":
    unittest.main()
