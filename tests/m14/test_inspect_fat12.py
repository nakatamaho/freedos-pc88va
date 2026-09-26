#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Synthetic FAT12 result checks, including shared and straddling entries."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("m14_fat12", ROOT / "tools/m14/inspect_fat12.py")
FAT12 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FAT12)
from build_media import build_d88, build_raw_image, set_fat12_entry  # noqa: E402


class Fat12ResultTests(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads((ROOT / "config/m05/media.json").read_text())
        self.layout = FAT12.derive_layout(self.spec)
        self.payloads = {"DATA.BIN": b"D" * 1025, "CONTROL.TXT": b"control"}
        self.raw = self.make_raw(self.payloads)
        fs = self.spec["filesystem"]
        self.fat_start = fs["reserved_sectors"] * 1024
        self.fat_size = fs["sectors_per_fat"] * 1024
        self.root_start = self.fat_start + fs["fat_count"] * self.fat_size

    def make_raw(self, payloads):
        records = [{"dos_name": name, "size": len(data), "data": data,
                    "sha256": hashlib.sha256(data).hexdigest(), "source_date_epoch": 1787814827}
                   for name, data in payloads.items()]
        return build_raw_image(self.spec, self.layout, records)[0]

    def inspect(self, raw):
        return FAT12.inspect(build_d88(self.spec, bytes(raw)), self.spec)

    def test_even_odd_and_fat_sector_straddling_entry(self):
        # Entry 682 occupies bytes 1023/1024 and is representable in this BPB.
        data = b"N" * (682 * 1024)
        summary, files = self.inspect(self.make_raw({"LARGE.BIN": data, "NEXT.BIN": b"next"}))
        self.assertEqual(files, {"LARGE.BIN": data, "NEXT.BIN": b"next"})
        self.assertIn(682, summary["files"]["LARGE.BIN"]["clusters"])
        self.assertEqual(summary["files"]["NEXT.BIN"]["clusters"], [684])
        self.assertTrue(summary["fat_copies_equal"])

    def test_deleted_records_and_residual_free_bytes_are_not_leaks(self):
        raw = bytearray(self.raw)
        offset = self.root_start + 64
        raw[offset:offset + 32] = b"\xE5" + b"X" * 31
        free_data = (self.layout["first_data_sector"] + 20) * 1024
        raw[free_data:free_data + 1024] = b"old bytes".ljust(1024, b"!")
        _, files = self.inspect(raw)
        self.assertEqual(files, self.payloads)

    def test_corrupt_shared_byte_at_fat_sector_boundary_is_rejected(self):
        # Entries 682 and 683 share byte 1024. Corrupt each side of that
        # byte in both mirrors, so mirror equality cannot hide a bad chain.
        original = self.make_raw({"LARGE.BIN": b"N" * (684 * 1024),
                                  "CONTROL.TXT": b"control"})
        for mask in (0x01, 0x10):
            raw = bytearray(original)
            for copy in range(self.spec["filesystem"]["fat_count"]):
                raw[self.fat_start + copy * self.fat_size + 1024] ^= mask
            with self.subTest(mask=mask), self.assertRaises(ValueError):
                self.inspect(raw)

    def test_cycles_crosslinks_leaks_lengths_and_mirrors_fail(self):
        for kind in ("cycle", "crosslink", "orphan", "length", "mirror", "bad"):
            raw = bytearray(self.raw)
            if kind == "crosslink":
                struct.pack_into("<H", raw, self.root_start + 32 + 26, 2)
            elif kind == "length":
                struct.pack_into("<I", raw, self.root_start + 28, 1)
            elif kind == "mirror":
                raw[self.fat_start + self.fat_size + 3] ^= 1
            else:
                cluster, value = {"cycle": (3, 2), "orphan": (8, 0xFFF), "bad": (3, 0xFF7)}[kind]
                for copy in range(2):
                    offset = self.fat_start + copy * self.fat_size
                    fat = raw[offset:offset + self.fat_size]
                    set_fat12_entry(fat, cluster, value)
                    raw[offset:offset + self.fat_size] = fat
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.inspect(raw)

    def test_subdirectory_empty_file_and_parent_links(self):
        raw = bytearray(self.raw)

        def directory_entry(name, attribute, cluster):
            entry = bytearray(32)
            entry[:11] = name
            entry[11] = attribute
            struct.pack_into("<H", entry, 26, cluster)
            return entry

        raw[self.root_start + 64:self.root_start + 96] = directory_entry(b"SUB        ", 0x10, 5)
        for copy in range(2):
            offset = self.fat_start + copy * self.fat_size
            fat = raw[offset:offset + self.fat_size]
            set_fat12_entry(fat, 5, 0xFFF)
            raw[offset:offset + self.fat_size] = fat
        data_start = (self.layout["first_data_sector"] + 3) * 1024
        raw[data_start:data_start + 32] = directory_entry(b".          ", 0x10, 5)
        raw[data_start + 32:data_start + 64] = directory_entry(b"..         ", 0x10, 0)
        raw[data_start + 64:data_start + 96] = directory_entry(b"EMPTY   TXT", 0x20, 0)
        summary, files = self.inspect(raw)
        self.assertEqual(summary["directories"], {"SUB": {"clusters": [5]}})
        self.assertEqual(files, dict(self.payloads, **{"SUB/EMPTY.TXT": b""}))
        for kind in ("parent", "missing", "crosslink"):
            bad = bytearray(raw)
            if kind == "parent":
                struct.pack_into("<H", bad, data_start + 32 + 26, 5)
            elif kind == "missing":
                bad[data_start] = 0xE5
            else:
                bad[self.root_start + 96:self.root_start + 128] = directory_entry(b"OTHER      ", 0x10, 5)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.inspect(bad)

    def test_volume_labels_are_not_short_filenames(self):
        raw = bytearray(self.raw)
        entry = bytearray(32)
        entry[:11] = b"VOLUME NAME"
        entry[11] = 8
        raw[self.root_start + 64:self.root_start + 96] = entry
        summary, files = self.inspect(raw)
        self.assertEqual(summary["volume_label"], "VOLUME NAME")
        self.assertEqual(files, self.payloads)
        raw[self.root_start + 96:self.root_start + 128] = entry
        with self.assertRaises(ValueError):
            self.inspect(raw)


if __name__ == "__main__":
    unittest.main()
