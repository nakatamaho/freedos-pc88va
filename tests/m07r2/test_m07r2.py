#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""ROM-free structural and fail-closed tests for M07R2."""

from __future__ import annotations

import importlib.util
import json
import struct
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


D88 = load("m07r2_d88", "tools/m07r2/d88.py")
TRACE = load("m07r2_trace", "tools/m07r2/trace_boundaries.py")
VERIFY = load("m07r2_verify", "tools/m07r2/verify_m07r2.py")


def synthetic_d88(*, tracks: int = 2, sectors: int = 2, size_code: int = 1) -> bytes:
    sector_size = 128 << size_code
    track_size = sectors * (16 + sector_size)
    total = 688 + tracks * track_size
    image = bytearray(total)
    image[:8] = b"FICTION\x00"
    image[26] = 1
    image[27] = 0x10
    struct.pack_into("<I", image, 28, total)
    cursor = 688
    for track in range(tracks):
        struct.pack_into("<I", image, 32 + track * 4, cursor)
        cylinder, head = divmod(track, 2)
        for sector in range(sectors):
            struct.pack_into(
                "<BBBBHBBBB3sBH",
                image,
                cursor,
                cylinder,
                head,
                sector + 1,
                size_code,
                sectors,
                0,
                0,
                0,
                0,
                bytes(3),
                0,
                sector_size,
            )
            cursor += 16
            image[cursor:cursor + sector_size] = bytes([track * 17 + sector]) * sector_size
            cursor += sector_size
    return bytes(image)


class D88ParserTests(unittest.TestCase):
    def test_valid_synthetic_structure(self) -> None:
        parsed = D88.parse(synthetic_d88())
        self.assertEqual(len(parsed.tracks), 2)
        self.assertEqual(parsed.sector_count, 4)
        self.assertTrue(parsed.write_protected)

    def test_truncated_header_is_rejected(self) -> None:
        with self.assertRaisesRegex(D88.D88Error, "header"):
            D88.parse(bytes(100))

    def test_declared_size_mismatch_is_rejected(self) -> None:
        image = bytearray(synthetic_d88())
        struct.pack_into("<I", image, 28, len(image) + 1)
        with self.assertRaisesRegex(D88.D88Error, "declared"):
            D88.parse(bytes(image))

    def test_descending_or_overlapping_offset_is_rejected(self) -> None:
        image = bytearray(synthetic_d88())
        struct.pack_into("<I", image, 36, 688)
        with self.assertRaisesRegex(D88.D88Error, "offset"):
            D88.parse(bytes(image))

    def test_offset_after_hole_is_rejected(self) -> None:
        image = bytearray(synthetic_d88())
        second = struct.unpack_from("<I", image, 36)[0]
        struct.pack_into("<I", image, 36, 0)
        struct.pack_into("<I", image, 40, second)
        with self.assertRaisesRegex(D88.D88Error, "empty"):
            D88.parse(bytes(image))

    def test_truncated_sector_is_rejected(self) -> None:
        image = bytearray(synthetic_d88())
        image = image[:-1]
        struct.pack_into("<I", image, 28, len(image))
        with self.assertRaisesRegex(D88.D88Error, "truncated|count"):
            D88.parse(bytes(image))

    def test_inconsistent_sector_size_is_rejected(self) -> None:
        image = bytearray(synthetic_d88())
        struct.pack_into("<H", image, 688 + 14, 128)
        with self.assertRaisesRegex(D88.D88Error, "size"):
            D88.parse(bytes(image))

    def test_duplicate_chr_is_rejected(self) -> None:
        image = bytearray(synthetic_d88())
        second_record = 688 + 16 + 256
        image[second_record:second_record + 3] = image[688:691]
        with self.assertRaisesRegex(D88.D88Error, "duplicate"):
            D88.parse(bytes(image))


class BoundaryTests(unittest.TestCase):
    def boundaries(self, *names: str):
        return TRACE.Boundaries(tuple(names))

    def test_class_a_positive_control_failure(self) -> None:
        self.assertEqual(TRACE.classify(self.boundaries(), None), "A")

    def test_class_b_probe_never_requests_a_read(self) -> None:
        control = self.boundaries(*TRACE.BOUNDARIES[:7])
        probe = self.boundaries(*TRACE.BOUNDARIES[:3])
        self.assertEqual(TRACE.classify(control, probe), "B")

    def test_class_c_probe_read_does_not_transfer(self) -> None:
        control = self.boundaries(*TRACE.BOUNDARIES[:7])
        probe = self.boundaries(*TRACE.BOUNDARIES[:4])
        self.assertEqual(TRACE.classify(control, probe), "C")

    def test_class_d_transfer_does_not_reach_marker(self) -> None:
        control = self.boundaries(*TRACE.BOUNDARIES[:7])
        probe = self.boundaries(*TRACE.BOUNDARIES[:7])
        self.assertEqual(TRACE.classify(control, probe), "D")

    def test_class_e_marker_reached(self) -> None:
        all_boundaries = self.boundaries(*TRACE.BOUNDARIES)
        self.assertEqual(TRACE.classify(all_boundaries, all_boundaries), "E")

    def test_divergence_reports_first_abstract_difference(self) -> None:
        control = self.boundaries(*TRACE.BOUNDARIES[:6])
        probe = self.boundaries(*TRACE.BOUNDARIES[:4])
        self.assertEqual(
            TRACE.divergence(control, probe),
            ("first_read_request", "first_successful_sector_transfer"),
        )

    def test_out_of_order_boundary_is_rejected(self) -> None:
        with self.assertRaisesRegex(TRACE.BoundaryError, "ordered"):
            self.boundaries("first_read_request", "firmware_fdd_request")


class PublicStatusTests(unittest.TestCase):
    def test_public_status_is_class_a_and_fully_redacted(self) -> None:
        status = json.loads(VERIFY.STATUS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(status["classification"], "A")
        self.assertFalse(status["private_gate"]["control_established"])
        self.assertEqual(status["private_gate"]["probe_variant_trial_count"], 0)
        self.assertFalse(status["private_policy"]["concrete_values_published"])
        self.assertFalse(status["m08_started"])

    def test_schema_rejects_claimed_control_success(self) -> None:
        status = json.loads(VERIFY.STATUS_PATH.read_text(encoding="utf-8"))
        schema = json.loads(VERIFY.SCHEMA_PATH.read_text(encoding="utf-8"))
        status["private_gate"]["control_established"] = True
        with self.assertRaisesRegex(VERIFY.M07R2Error, "constant"):
            VERIFY.validate_schema(status, schema)

    def test_schema_rejects_a_private_value_field(self) -> None:
        status = json.loads(VERIFY.STATUS_PATH.read_text(encoding="utf-8"))
        schema = json.loads(VERIFY.SCHEMA_PATH.read_text(encoding="utf-8"))
        status["private_gate"]["observed_value"] = "synthetic"
        with self.assertRaisesRegex(VERIFY.M07R2Error, "additional"):
            VERIFY.validate_schema(status, schema)

    def test_private_path_marker_is_detected_without_a_real_path_fixture(self) -> None:
        synthetic = "/" + "Users" + "/example/private"
        with self.assertRaisesRegex(VERIFY.M07R2Error, "private-data"):
            VERIFY.validate_public_payload(synthetic)


if __name__ == "__main__":
    unittest.main()
