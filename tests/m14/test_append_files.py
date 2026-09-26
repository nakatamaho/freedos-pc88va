#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Synthetic-only checks for non-reallocating disposable input preparation."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("m14_append", ROOT / "tools/m14/append_files.py")
APPEND = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(APPEND)
from build_media import build_d88, build_raw_image, set_fat12_entry  # noqa: E402
from common import ValidationError  # noqa: E402


class AppendFilesTests(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads((ROOT / "config/m05/media.json").read_text())
        self.layout = APPEND.derive_layout(self.spec)
        content = b"untouched original\n" * 80
        record = {"dos_name": "ORIGINAL.BIN", "data": content, "size": len(content),
                  "sha256": hashlib.sha256(content).hexdigest(), "source_date_epoch": 1787814827}
        self.raw, _ = build_raw_image(self.spec, self.layout, [record])
        self.bps = self.spec["geometry"]["bytes_per_sector"]
        fs = self.spec["filesystem"]
        self.fat_start = fs["reserved_sectors"] * self.bps
        self.fat_size = fs["sectors_per_fat"] * self.bps
        self.root_start = self.fat_start + fs["fat_count"] * self.fat_size

    def test_exact_preservation_and_deterministic_additions(self):
        base = build_d88(self.spec, self.raw)
        additions = {"PROBE.COM": b"test" * 300, "MEDIA.TXT": b"original fixture\n"}
        result, record = APPEND.append_files(base, additions, self.spec)
        repeated, _ = APPEND.append_files(base, dict(reversed(list(additions.items()))), self.spec)
        self.assertEqual(result, repeated)
        _, raw = APPEND.parse_d88(result, self.spec, self.layout)
        self.assertEqual(raw[:self.fat_start], self.raw[:self.fat_start])
        self.assertEqual(raw[self.root_start:self.root_start + 32], self.raw[self.root_start:self.root_start + 32])
        data_start = self.layout["first_data_sector"] * self.bps
        self.assertEqual(raw[data_start:data_start + 2 * self.bps], self.raw[data_start:data_start + 2 * self.bps])
        expected = bytearray(self.raw)
        for index, (name, data) in enumerate(sorted(additions.items())):
            chain = record["allocations"][name]
            actual = b"".join(raw[data_start + (c - 2) * self.bps:data_start + (c - 1) * self.bps] for c in chain)
            self.assertEqual(actual[:len(data)], data)
            self.assertEqual(actual[len(data):], bytes(len(actual) - len(data)))
            for position, cluster in enumerate(chain):
                start = data_start + (cluster - 2) * self.bps
                expected[start:start + self.bps] = data[position * self.bps:(position + 1) * self.bps].ljust(self.bps, b"\0")
                for copy in range(2):
                    offset = self.fat_start + copy * self.fat_size
                    fat = expected[offset:offset + self.fat_size]
                    set_fat12_entry(fat, cluster, chain[position + 1] if position + 1 < len(chain) else 0xFFF)
                    expected[offset:offset + self.fat_size] = fat
            offset = self.root_start + (index + 1) * 32
            # All newly allocated root bytes are separately decoded below.
            expected[offset:offset + 32] = raw[offset:offset + 32]
            self.assertEqual(raw[offset:offset + 11], APPEND.encode_dos_name(name))
            self.assertEqual(struct.unpack_from("<HI", raw, offset + 26), (chain[0], len(data)))
        self.assertEqual(raw, expected)
        self.assertEqual(result, build_d88(self.spec, bytes(expected)))

    def test_collisions_invalid_names_and_capacity_fail_closed(self):
        base = build_d88(self.spec, self.raw)
        for additions in ({}, {"ORIGINAL.BIN": b"replace"}, {"lower.com": b"x"},
                          {"EMPTY.COM": b""}, {"HUGE.BIN": bytes(len(self.raw))},
                          {f"F{i:04}.COM": b"x" for i in range(self.spec["filesystem"]["root_entries"])}):
            with self.subTest(names=list(additions)[:2]), self.assertRaises((ValueError, ValidationError)):
                APPEND.append_files(base, additions, self.spec)

    def test_malformed_input_is_not_repaired_or_reallocated(self):
        for kind in ("bpb", "mirror", "cycle", "short", "orphan", "length", "directory"):
            raw = bytearray(self.raw)
            if kind == "bpb":
                raw[11] ^= 1
            elif kind == "mirror":
                raw[self.fat_start + self.fat_size + 3] ^= 1
            elif kind == "length":
                struct.pack_into("<I", raw, self.root_start + 28, len(raw))
            elif kind == "directory":
                raw[self.root_start + 11] = 0x10
            else:
                fat = raw[self.fat_start:self.fat_start + self.fat_size]
                cluster, value = {"cycle": (3, 2), "short": (2, 0xFFF), "orphan": (8, 0xFFF)}[kind]
                set_fat12_entry(fat, cluster, value)
                for copy in range(2):
                    offset = self.fat_start + copy * self.fat_size
                    raw[offset:offset + self.fat_size] = fat
            with self.subTest(kind=kind), self.assertRaises((ValueError, ValidationError)):
                APPEND.append_files(build_d88(self.spec, bytes(raw)), {"PROBE.COM": b"x"}, self.spec)


if __name__ == "__main__":
    unittest.main()
