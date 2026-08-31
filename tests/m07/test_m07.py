#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Fail-closed public tests for the M07 boot-acceptance probe harness."""

from __future__ import annotations

import copy
import importlib.util
import struct
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("m07_harness", ROOT / "tools/m07/m07.py")
assert SPEC and SPEC.loader
M07 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M07
SPEC.loader.exec_module(M07)


class M07Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = (ROOT / "qa/results/m06/run-1/media/pc88va-m06-compile-only.img").read_bytes()
        cls.common, cls.builder, cls.inspector = M07.m05_modules()
        cls.media_spec, cls.derived = cls.common.validate_spec(ROOT)

    def item(self, variant_id: str) -> dict:
        return next(item for item in M07.config()["variants"] if item["id"] == variant_id)

    def test_probe_is_exact_minimal_code(self) -> None:
        M07.validate_probe_bytes(M07.PROBE_BYTES)
        self.assertEqual(M07.PROBE_BYTES, bytes.fromhex("9087db87c987d2ebfe"))

    def test_probe_exceeding_sector_is_rejected(self) -> None:
        with self.assertRaises(M07.M07Error):
            M07.validate_probe_layout(1023, b"\x90\x90")

    def test_probe_overlapping_bpb_is_rejected(self) -> None:
        with self.assertRaises(M07.M07Error):
            M07.validate_probe_layout(61, b"\x90")

    def test_probe_io_opcode_is_rejected(self) -> None:
        with self.assertRaisesRegex(M07.M07Error, "io"):
            M07.validate_probe_bytes(b"\xe4")

    def test_probe_interrupt_opcode_is_rejected(self) -> None:
        with self.assertRaisesRegex(M07.M07Error, "interrupt"):
            M07.validate_probe_bytes(b"\xcd")

    def test_probe_stack_opcode_is_rejected(self) -> None:
        with self.assertRaisesRegex(M07.M07Error, "stack"):
            M07.validate_probe_bytes(b"\x50")

    def test_probe_call_opcode_is_rejected(self) -> None:
        with self.assertRaisesRegex(M07.M07Error, "call"):
            M07.validate_probe_bytes(b"\xe8")

    def test_probe_return_opcode_is_rejected(self) -> None:
        with self.assertRaisesRegex(M07.M07Error, "return"):
            M07.validate_probe_bytes(b"\xc3")

    def test_probe_ambient_path_bytes_are_rejected(self) -> None:
        with self.assertRaisesRegex(M07.M07Error, "ambient"):
            M07.validate_probe_bytes(b"/Users/example")

    def test_all_public_variants_preserve_non_boot_sectors(self) -> None:
        for item in M07.config()["variants"]:
            raw, _ = M07.build_variant(self.base, M07.PROBE_BYTES, item)
            self.assertEqual(raw[1024:], self.base[1024:])
            self.assertEqual(raw[3:62], self.base[3:62])

    def test_variant_outside_overlay_is_rejected(self) -> None:
        item = self.item("V01")
        raw, _ = M07.build_variant(self.base, M07.PROBE_BYTES, item)
        changed = bytearray(raw)
        changed[2048] ^= 1
        with self.assertRaisesRegex(M07.M07Error, "FAT, root directory"):
            M07.validate_variant(self.base, bytes(changed), item, [[0, 3], [62, 1024]])

    def test_variant_wrong_signature_510_is_rejected(self) -> None:
        item = self.item("V02")
        raw, _ = M07.build_variant(self.base, M07.PROBE_BYTES, item)
        changed = bytearray(raw)
        changed[510:512] = b"\x00\x00"
        with self.assertRaisesRegex(M07.M07Error, "510"):
            M07.validate_variant(self.base, bytes(changed), item, [[0, 3], [62, 1024]])

    def test_variant_wrong_signature_1022_is_rejected(self) -> None:
        item = self.item("V03")
        raw, _ = M07.build_variant(self.base, M07.PROBE_BYTES, item)
        changed = bytearray(raw)
        changed[1022:1024] = b"\x00\x00"
        with self.assertRaisesRegex(M07.M07Error, "1022"):
            M07.validate_variant(self.base, bytes(changed), item, [[0, 3], [62, 1024]])

    def test_v00_undeclared_signature_is_rejected(self) -> None:
        item = self.item("V00")
        changed = bytearray(self.base)
        changed[510:512] = M07.SIGNATURE
        with self.assertRaises(M07.M07Error):
            M07.validate_variant(self.base, bytes(changed), item, [[510, 512]])

    def test_v01_undeclared_signature_is_rejected(self) -> None:
        item = self.item("V01")
        sector = M07.make_probe_sector(self.base[:1024], M07.PROBE_BYTES, False, False)
        self.assertNotEqual(sector[510:512], M07.SIGNATURE)
        self.assertNotEqual(sector[1022:1024], M07.SIGNATURE)

    def test_d88_round_trip_is_exact_for_all_variants(self) -> None:
        for item in M07.config()["variants"]:
            raw, _ = M07.build_variant(self.base, M07.PROBE_BYTES, item)
            d88 = self.builder.build_d88(self.media_spec, raw)
            _, extracted = self.inspector.parse_d88(d88, self.media_spec, self.derived)
            self.assertEqual(extracted, raw)

    def test_truncated_d88_is_rejected(self) -> None:
        d88 = self.builder.build_d88(self.media_spec, self.base)
        with self.assertRaises(self.common.ValidationError):
            self.inspector.parse_d88(d88[:600], self.media_spec, self.derived)

    def test_descending_d88_offsets_are_rejected(self) -> None:
        d88 = bytearray(self.builder.build_d88(self.media_spec, self.base))
        struct.pack_into("<I", d88, 36, 688)
        with self.assertRaises(self.common.ValidationError):
            self.inspector.parse_d88(bytes(d88), self.media_spec, self.derived)

    def test_duplicate_d88_sector_is_rejected(self) -> None:
        d88 = bytearray(self.builder.build_d88(self.media_spec, self.base))
        record_size = 16 + 1024
        d88[688 + record_size + 2] = 1
        with self.assertRaises(self.common.ValidationError):
            self.inspector.parse_d88(bytes(d88), self.media_spec, self.derived)

    def test_wrong_d88_sector_size_code_is_rejected(self) -> None:
        d88 = bytearray(self.builder.build_d88(self.media_spec, self.base))
        d88[688 + 3] = 2
        with self.assertRaises(self.common.ValidationError):
            self.inspector.parse_d88(bytes(d88), self.media_spec, self.derived)

    def test_d88_error_status_is_rejected(self) -> None:
        d88 = bytearray(self.builder.build_d88(self.media_spec, self.base))
        d88[688 + 8] = 1
        with self.assertRaises(self.common.ValidationError):
            self.inspector.parse_d88(bytes(d88), self.media_spec, self.derived)

    def test_d88_extraction_mismatch_is_detectable(self) -> None:
        changed = bytearray(self.base)
        changed[800] ^= 1
        d88 = self.builder.build_d88(self.media_spec, bytes(changed))
        _, extracted = self.inspector.parse_d88(d88, self.media_spec, self.derived)
        self.assertNotEqual(extracted, self.base)

    def test_wrong_m06_kernel_identity_is_rejected(self) -> None:
        with self.assertRaises(M07.M07Error):
            M07.validate_kernel_role({"size": 83774, "sha256": "0" * 64})

    def test_generated_image_or_trace_staging_is_rejected(self) -> None:
        for path in ("qa/results/m07/run.img", "evidence/session.log"):
            with self.subTest(path=path), self.assertRaises(M07.M07Error):
                M07.validate_staged_paths([path])

    def test_private_and_component_staging_is_rejected(self) -> None:
        for path in ("notes/private-analysis/result.json", "components/fdkernel"):
            with self.subTest(path=path), self.assertRaises(M07.M07Error):
                M07.validate_staged_paths([path])

    def test_public_text_private_markers_are_rejected(self) -> None:
        for text in ("file:///tmp/input", "secret-va.rom", "/Users/example/input"):
            with self.subTest(text=text), self.assertRaises(M07.M07Error):
                M07.scan_public_text(text)

    def test_public_result_rejects_private_values(self) -> None:
        result = self.not_performed_result()
        result["registers"] = {"AX": 0}
        with self.assertRaises(M07.M07Error):
            M07.validate_public_result(result)

    def test_private_overlay_without_nonpromotion_is_rejected(self) -> None:
        private = self.private_result()
        private["public_promotion_status"] = "approved"
        with self.assertRaises(M07.M07Error):
            M07.redact_private_result(private)

    def test_redactor_publishes_names_and_counts_but_no_values(self) -> None:
        private = self.private_result()
        private["questions"]["entry_cs_ip"] = {
            "classification": "PRIVATE_VAEG_OBSERVATION",
            "resolved": True,
            "value": {"private": "synthetic-only"},
        }
        public = M07.redact_private_result(private)
        self.assertIn("entry_cs_ip", public["resolved_fields"])
        self.assertNotIn("values", public)
        self.assertNotIn("questions", public)

    def test_not_performed_result_must_be_internally_consistent(self) -> None:
        result = self.not_performed_result()
        result["trial_count"] = 1
        with self.assertRaises(M07.M07Error):
            M07.validate_public_result(result)

    def test_component_gitlink_drift_is_rejected(self) -> None:
        expected = dict(M07.EXPECTED_GITLINKS)
        expected["components/fdkernel"] = "0" * 40
        with self.assertRaises(M07.M07Error):
            M07.validate_components(expected)

    def test_public_workflow_does_not_invoke_private_gate_or_vaeg(self) -> None:
        workflow = (ROOT / ".github/workflows/m07-probe.yml").read_text(encoding="utf-8")
        lower = workflow.lower()
        self.assertNotIn("m07-private", lower)
        self.assertNotIn("--roms", lower)
        self.assertNotIn("m07_private_result", workflow)

    @staticmethod
    def private_result() -> dict:
        return {
            "input_preservation": "passed",
            "private_gate_result": "inconclusive",
            "public_promotion_status": "prohibited_pending_user_approval",
            "questions": {
                name: {"classification": "UNKNOWN", "resolved": False, "value": None}
                for name in M07.QUESTION_FIELDS
            },
            "schema_version": 1,
            "trial_count": 10,
            "variant_count": 5,
        }

    @staticmethod
    def not_performed_result() -> dict:
        return {
            "input_preservation": "not_performed",
            "private_gate": "not_performed",
            "private_gate_result": "not_performed",
            "public_promotion_status": "prohibited_pending_user_approval",
            "resolved_field_count": 0,
            "resolved_fields": [],
            "schema_version": 1,
            "trial_count": 0,
            "unresolved_field_count": len(M07.QUESTION_FIELDS),
            "unresolved_fields": sorted(M07.QUESTION_FIELDS),
            "variant_count": 5,
        }


if __name__ == "__main__":
    unittest.main()
