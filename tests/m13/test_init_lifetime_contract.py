#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Reject linked initializer regressions without proprietary inputs."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/m13'))
from verify_linked_placement import verify_init_ownership


class InitOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.load = 0x1000
        self.interval = (0x13000, 0x13100)
        self.syms = {name: (0x300, i * 16) for i, name in enumerate(
            ('DynAlloc_', 'DynFree_', 'DynLast_', 'dsk_init_'))}
        self.syms.update({name: (0x200, i * 16) for i, name in enumerate(
            ('_P_0', 'init_fatal_', 'pc88va_release_boot_memory_'))})

    def check(self):
        verify_init_ownership(self.syms, self.interval, self.load)

    def test_disposable_entries_and_resident_consumers(self):
        self.check()

    def test_equivalent_segment_offset_is_same_storage(self):
        self.syms['dsk_init_'] = (0x2ff, 0x40)
        self.check()

    def test_each_initializer_left_resident_is_rejected(self):
        for name in ('DynAlloc_', 'DynFree_', 'DynLast_', 'dsk_init_'):
            with self.subTest(name=name):
                original = self.syms[name]
                self.syms[name] = (0x200, 0)
                with self.assertRaisesRegex(ValueError, 'incorrect linked lifetime'):
                    self.check()
                self.syms[name] = original

    def test_each_live_consumer_in_reclaimed_code_is_rejected(self):
        for name in ('_P_0', 'init_fatal_', 'pc88va_release_boot_memory_'):
            with self.subTest(name=name):
                original = self.syms[name]
                self.syms[name] = (0x300, 0)
                with self.assertRaisesRegex(ValueError, 'incorrect linked lifetime'):
                    self.check()
                self.syms[name] = original

    def test_end_exclusive_and_missing_symbols(self):
        self.syms['DynAlloc_'] = (0x310, 0)
        with self.assertRaises(ValueError):
            self.check()
        del self.syms['DynAlloc_']
        with self.assertRaisesRegex(ValueError, 'missing lifetime symbol'):
            self.check()


if __name__ == '__main__':
    unittest.main()
