#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Positive and fail-closed tests for deterministic M05 media tooling."""

from __future__ import annotations

import copy
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/m05"))

from build_media import build_d88, build_raw_image, set_fat12_entry  # noqa: E402
from common import (  # noqa: E402
    EXPECTED_GITLINKS,
    ValidationError,
    canonical_json_bytes,
    chs_to_lba,
    derive_layout,
    encode_dos_name,
    fat_datetime,
    lba_to_chs,
    reject_ambient_metadata,
    sha256_bytes,
    validate_chs_round_trip,
    validate_component_contract,
    validate_payload_contract,
    validate_schema_contract,
)
from compare_media import compare_runs  # noqa: E402
from inspect_media import inspect_raw, parse_d88, validate_d88_round_trip  # noqa: E402
from verify_m05 import validate_descendant_paths  # noqa: E402


def load_spec():
    return json.loads((ROOT / "config/m05/media.json").read_text(encoding="utf-8"))


def synthetic_record(name, data, epoch=946684800):
    return {
        "data": data,
        "dos_name": name,
        "sha256": sha256_bytes(data),
        "size": len(data),
        "source_date_epoch": epoch,
    }


def expected_record(record):
    return {
        "dos_name": record["dos_name"],
        "sha256": record["sha256"],
        "size": record["size"],
        "source_date_epoch": record["source_date_epoch"],
    }


class MediaFixture(unittest.TestCase):
    def setUp(self):
        self.spec = load_spec()
        self.derived = derive_layout(self.spec)
        self.records = [
            synthetic_record("KERNEL.SYS", b"K" * 2500),
            synthetic_record("COMMAND.COM", b"C" * 1300),
            synthetic_record("COUNTRY.SYS", b"N" * 700),
        ]
        self.raw, self.summary = build_raw_image(self.spec, self.derived, self.records)
        self.d88 = build_d88(self.spec, self.raw)
        self.expected = [expected_record(item) for item in self.records]

    def reject_raw(self, raw=None, expected=None, spec=None, derived=None):
        with self.assertRaises(ValidationError):
            inspect_raw(
                self.raw if raw is None else raw,
                self.spec if spec is None else spec,
                self.derived if derived is None else derived,
                self.expected if expected is None else expected,
            )

    def mutate_fat_entry(self, raw, cluster, value):
        result = bytearray(raw)
        bps = self.spec["geometry"]["bytes_per_sector"]
        fat_size = self.spec["filesystem"]["sectors_per_fat"] * bps
        for lba in (1, 3):
            start = lba * bps
            fat = bytearray(result[start:start + fat_size])
            set_fat12_entry(fat, cluster, value)
            result[start:start + fat_size] = fat
        return bytes(result)


class MediaPositiveTests(MediaFixture):
    def test_geometry_and_chs_lba_round_trip(self):
        self.assertEqual(self.derived["total_bytes"], 1310720)
        self.assertEqual(self.derived["first_data_sector"], 11)
        self.assertEqual(self.derived["data_clusters"], 1269)
        validate_chs_round_trip(self.spec["geometry"])
        self.assertEqual(lba_to_chs(1279, self.spec["geometry"]), (79, 1, 8))
        self.assertEqual(chs_to_lba(79, 1, 8, self.spec["geometry"]), 1279)

    def test_fat12_image_and_payloads_validate(self):
        summary, extracted = inspect_raw(self.raw, self.spec, self.derived, self.expected)
        self.assertEqual(sorted(extracted), ["COMMAND.COM", "COUNTRY.SYS", "KERNEL.SYS"])
        self.assertEqual(summary["fat_1"], summary["fat_2"])
        self.assertEqual(extracted["KERNEL.SYS"], self.records[0]["data"])

    def test_d88_round_trip_is_exact(self):
        summary, reconstructed = validate_d88_round_trip(self.d88, self.raw, self.spec, self.derived)
        self.assertEqual(summary["populated_tracks"], 160)
        self.assertEqual(summary["sector_count"], 1280)
        self.assertEqual(reconstructed, self.raw)

    def test_timestamp_is_fixed_utc_and_even_second(self):
        date, time, rendered = fat_datetime(946684801)
        self.assertIsInstance(date, int)
        self.assertIsInstance(time, int)
        self.assertEqual(rendered, "2000-01-01T00:00:00Z")

    def test_canonical_json_has_sorted_keys_and_final_newline(self):
        self.assertEqual(canonical_json_bytes({"z": 1, "a": 2}), b'{\n  "a": 2,\n  "z": 1\n}\n')


class MediaNegativeTests(MediaFixture):
    def test_wrong_raw_image_size_is_rejected(self):
        self.reject_raw(self.raw[:-1])

    def test_wrong_bpb_sector_size_and_sector_count_are_rejected(self):
        for offset, value in ((11, 512), (19, 1279)):
            broken = bytearray(self.raw)
            struct.pack_into("<H", broken, offset, value)
            with self.subTest(offset=offset):
                self.reject_raw(bytes(broken))

    def test_invalid_chs_and_lba_are_rejected(self):
        for call in (
            lambda: chs_to_lba(80, 0, 1, self.spec["geometry"]),
            lambda: chs_to_lba(0, 2, 1, self.spec["geometry"]),
            lambda: chs_to_lba(0, 0, 0, self.spec["geometry"]),
            lambda: lba_to_chs(1280, self.spec["geometry"]),
        ):
            with self.assertRaises(ValidationError):
                call()

    def test_inconsistent_derived_layout_is_rejected(self):
        broken = copy.deepcopy(self.spec)
        broken["filesystem"]["first_data_sector"] = 12
        with self.assertRaises(ValidationError):
            derive_layout(broken)

    def test_schema_contract_drift_is_rejected(self):
        schema = json.loads((ROOT / "config/m05/media.schema.json").read_text(encoding="utf-8"))
        schema["additionalProperties"] = True
        with self.assertRaises(ValidationError):
            validate_schema_contract(schema, set(self.spec))

    def test_mismatched_fat_copies_are_rejected(self):
        broken = bytearray(self.raw)
        broken[3 * 1024 + 20] ^= 1
        self.reject_raw(bytes(broken))

    def test_noncanonical_fat12_entry_is_rejected(self):
        self.reject_raw(self.mutate_fat_entry(self.raw, 216, 1))

    def test_malformed_final_fat12_nibble_is_rejected(self):
        broken = bytearray(self.raw)
        final_byte = self.derived["fat_bytes_required"] - 1
        for lba in (1, 3):
            broken[lba * 1024 + final_byte] |= 0xF0
        self.reject_raw(bytes(broken))

    def test_cluster_chain_loop_is_rejected(self):
        self.reject_raw(self.mutate_fat_entry(self.raw, 2, 2))

    def test_cluster_cross_link_is_rejected(self):
        broken = bytearray(self.raw)
        root_second_entry_cluster = 5 * 1024 + 32 + 26
        struct.pack_into("<H", broken, root_second_entry_cluster, 2)
        self.reject_raw(bytes(broken))

    def test_directory_size_exceeding_chain_is_rejected(self):
        broken = bytearray(self.raw)
        first_size = 5 * 1024 + 28
        struct.pack_into("<I", broken, first_size, 5000)
        expected = copy.deepcopy(self.expected)
        expected[0]["size"] = 5000
        self.reject_raw(bytes(broken), expected=expected)

    def test_payload_sha256_mismatch_is_rejected(self):
        expected = copy.deepcopy(self.expected)
        expected[0]["sha256"] = "0" * 64
        self.reject_raw(expected=expected)

    def test_duplicate_dos_filename_is_rejected(self):
        broken = bytearray(self.raw)
        root = 5 * 1024
        broken[root + 32:root + 43] = broken[root:root + 11]
        self.reject_raw(bytes(broken))

    def test_invalid_or_lossy_filename_is_rejected(self):
        for name in ("lower.sys", "TOO-LONG9.SYS", "BAD/NAME.SYS", "日本語.SYS"):
            with self.subTest(name=name), self.assertRaises(ValidationError):
                encode_dos_name(name)

    def test_ambient_timestamp_and_private_path_are_rejected(self):
        for value in (
            {"generated_at": "2026-08-31T00:00:00Z"},
            {"source": "/absolute/private/input"},
            {"source": "private-source-root/manual.txt"},
        ):
            with self.assertRaises(ValidationError):
                reject_ambient_metadata(value)

    def test_fat_timestamp_out_of_range_is_rejected(self):
        with self.assertRaises(ValidationError):
            fat_datetime(0)

    def test_truncated_d88_header_and_sector_are_rejected(self):
        for broken in (self.d88[:687], self.d88[:-1]):
            with self.subTest(size=len(broken)), self.assertRaises(ValidationError):
                parse_d88(broken, self.spec, self.derived)

    def test_descending_or_overlapping_d88_offsets_are_rejected(self):
        broken = bytearray(self.d88)
        first = struct.unpack_from("<I", broken, 32)[0]
        struct.pack_into("<I", broken, 36, first)
        with self.assertRaises(ValidationError):
            parse_d88(bytes(broken), self.spec, self.derived)

    def test_duplicate_or_missing_d88_chr_is_rejected(self):
        broken = bytearray(self.d88)
        second_header = 688 + 16 + 1024
        broken[second_header + 2] = 1
        with self.assertRaises(ValidationError):
            parse_d88(bytes(broken), self.spec, self.derived)

    def test_wrong_d88_sector_size_code_is_rejected(self):
        broken = bytearray(self.d88)
        broken[688 + 3] = 2
        with self.assertRaises(ValidationError):
            parse_d88(bytes(broken), self.spec, self.derived)

    def test_nonzero_d88_deleted_or_error_status_is_rejected(self):
        for offset in (688 + 7, 688 + 8):
            broken = bytearray(self.d88)
            broken[offset] = 1
            with self.subTest(offset=offset), self.assertRaises(ValidationError):
                parse_d88(bytes(broken), self.spec, self.derived)

    def test_d88_extraction_mismatch_is_rejected(self):
        broken = bytearray(self.d88)
        broken[688 + 16] ^= 1
        with self.assertRaises(ValidationError):
            validate_d88_round_trip(bytes(broken), self.raw, self.spec, self.derived)

    def test_undeclared_boot_signature_is_rejected_at_both_offsets(self):
        for offset in (510, 1022):
            broken = bytearray(self.raw)
            broken[offset:offset + 2] = b"\x55\xaa"
            with self.subTest(offset=offset):
                self.reject_raw(bytes(broken))

    def test_wrong_country_artifact_is_rejected(self):
        records = accepted_contract_records()
        records[2]["source_role"] = "kernel-country-driver"
        records[2]["size"] = 30250
        with self.assertRaises(ValidationError):
            validate_payload_contract(records)

    def test_wrong_kernel_artifact_is_rejected(self):
        records = accepted_contract_records()
        records[0]["sha256"] = "0" * 64
        with self.assertRaises(ValidationError):
            validate_payload_contract(records)

    def test_component_gitlink_drift_is_rejected(self):
        broken = dict(EXPECTED_GITLINKS)
        broken["fdkernel"] = "0" * 40
        with self.assertRaises(ValidationError):
            validate_component_contract(broken)

    def test_two_run_byte_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run1 = root / "run-1"
            run2 = root / "run-2"
            run1.mkdir()
            run2.mkdir()
            (run1 / "candidate.img").write_bytes(b"one")
            (run2 / "candidate.img").write_bytes(b"two")
            self.assertEqual(compare_runs(run1, run2)["status"], "fail")

    def test_m07r1_descendant_paths_are_narrowly_allowed(self):
        validate_descendant_paths([
            "docs/porting/m07r1-production-trace-rerun.md",
            "schema/m07r1-public-status.schema.json",
        ])
        with self.assertRaises(ValidationError):
            validate_descendant_paths([
                "docs/porting/m07r1-unreviewed-result.md",
            ])

    def test_m07r2_descendant_paths_are_narrowly_allowed(self):
        validate_descendant_paths([
            ".github/workflows/m07-probe.yml",
            "config/m07/m07r2-public-status.json",
            "docs/porting/m07r2-positive-control-diagnosis.md",
            "qa/golden/m07r2-public-status.sha256",
            "schema/m07r2-public-status.schema.json",
            "tests/m07r2/test_m07r2.py",
            "tools/m07r2/verify_m07r2.py",
        ])
        with self.assertRaises(ValidationError):
            validate_descendant_paths([
                "docs/porting/m07r2-unreviewed-private-result.md",
            ])


def accepted_contract_records():
    return [
        {
            "dos_name": "KERNEL.SYS",
            "sha256": "3ebddb01abe5e39f16d27439836be283c57d454f012d3c990f01fa8a2b14101d",
            "size": 83774,
            "source_role": "kernel",
        },
        {
            "dos_name": "COMMAND.COM",
            "sha256": "fabe7744cc7c51c6f72519cc39d89bf77beaf908f994675a97a1e34c93549da1",
            "size": 91143,
            "source_role": "command-interpreter",
        },
        {
            "dos_name": "COUNTRY.SYS",
            "sha256": "04b2d2bc8df382090686f00e547d718d6706d22fb34c34dd77cd55083d5c34d5",
            "size": 42614,
            "source_role": "standalone-country-driver",
        },
    ]


if __name__ == "__main__":
    unittest.main()
