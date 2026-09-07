# SPDX-License-Identifier: GPL-2.0-or-later
"""Public synthetic tests; no firmware or private overlay is opened."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/m08"))
from media import compose, ValidationError, sha256_bytes


class MediaTests(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads((ROOT / "config/m05/media.json").read_text())
        self.records = [{"dos_name": name, "data": data, "size": len(data),
                         "sha256": sha256_bytes(data), "source_date_epoch": 946684800}
                        for name, data in (("KERNEL.SYS", b"MZ" + bytes(2048)),
                                           ("COMMAND.COM", b"synthetic command"),
                                           ("COUNTRY.SYS", b"synthetic country"))]
        self.stage2 = b"synthetic bootstrap extent" * 120

    def bootstrap(self, extent):
        self.assertEqual(set(extent), {"first_lba", "sector_count", "file_size"})
        self.assertGreater(extent["first_lba"], 11)
        self.assertEqual(extent["sector_count"], (len(self.stage2)+1023)//1024)
        result = bytearray(1024)
        result[:3] = b"\xeb\x3c\x90"
        result[62:64] = b"\xeb\xfe"
        return bytes(result)

    def test_two_build_identity_and_round_trip(self):
        args = (self.spec, self.records, self.stage2, self.bootstrap, {510: False, 1022: False})
        first, second = compose(*args), compose(*args)
        self.assertEqual(first, second)
        self.assertEqual((len(first[0]), len(first[1])), (1310720, 1331888))
        self.assertTrue(first[2]["payloads_verified"])

    def test_only_declared_signature_slots_change(self):
        first = compose(self.spec, self.records, self.stage2, self.bootstrap, {510: False, 1022: False})[0]
        second = compose(self.spec, self.records, self.stage2, self.bootstrap, {510: True, 1022: True})[0]
        self.assertEqual([i for i, (a, b) in enumerate(zip(first, second)) if a != b],
                         [510, 511, 1022, 1023])

    def test_bootstrap_bpb_signature_and_extent_overlap_rejected(self):
        for index in (3, 61, 510, 1023):
            def corrupt(extent):
                data = bytearray(self.bootstrap(extent))
                data[index] = 1
                return data
            with self.assertRaises(ValidationError):
                compose(self.spec, self.records, self.stage2, corrupt, {510: False, 1022: False})

    def test_payload_identity_mismatch_rejected(self):
        self.records[0]["data"] += b"changed"
        with self.assertRaises(ValidationError):
            compose(self.spec, self.records, self.stage2, self.bootstrap, {510: False, 1022: False})

    def test_undeclared_signature_or_payload_set_rejected(self):
        for signatures in ({510: False}, {510: 0, 1022: False}, {510: False, 1022: False, 100: True}):
            with self.assertRaises(ValidationError):
                compose(self.spec, self.records, self.stage2, self.bootstrap, signatures)
        with self.assertRaises(ValidationError):
            compose(self.spec, self.records[::-1], self.stage2, self.bootstrap, {510: False, 1022: False})


if __name__ == "__main__":
    unittest.main()
