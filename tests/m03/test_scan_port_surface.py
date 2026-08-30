#!/usr/bin/env python3
"""Focused scanner fixtures and fail-closed M03 verifier tests."""

import copy
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/m03"))

import scan_port_surface as scanner  # noqa: E402
import verify_m03 as verifier  # noqa: E402


class ScannerFixtureTests(unittest.TestCase):
    def test_minimal_rule_fixtures_match_declared_rules(self):
        fixtures = {
            "PATH-IBMCPC-DIRECTORY": ("path", "ibmpc/kernel/makefile"),
            "PATH-NEC98-DIRECTORY": ("path", "nec98/kernel/makefile"),
            "BUILD-PLATFORM-CONDITIONAL": ("content", b"#if defined(NEC98)"),
            "BUILD-INCLUDE-RELATION": ("content", b'#include "platform.h"'),
            "BOOT-LOADER-LAYOUT": ("content", b"B_FAT12 loader"),
            "DISK-FAT-BLOCK-IO": ("content", b"blockio sector geometry"),
            "DMA-FDC-SIGNAL": ("content", b"fdc dma floppy"),
            "CONSOLE-OUTPUT-SIGNAL": ("content", b"console display putc"),
            "CONSOLE-INPUT-SIGNAL": ("content", b"keyboard keycode input"),
            "TIMER-CLOCK-SIGNAL": ("content", b"timer clock tick"),
            "INTERRUPT-VECTOR-SIGNAL": ("content", b"interrupt vector iret"),
            "MEMORY-STARTUP-SIGNAL": ("content", b"memory segment startup"),
            "FIRMWARE-BIOS-SIGNAL": ("content", b"BIOS int 13"),
            "ASM-IO-OPERATION": ("content", b"in al, dx"),
            "ASM-INT-OPERATION": ("content", b"iret"),
            "NLS-DBCS-SIGNAL": ("content", b"country DBCS codepage"),
            "DEVICE-INIT-SIGNAL": ("content", b"device driver init"),
            "EXEC-RUNTIME-SIGNAL": ("content", b"command shell spawn"),
            "COMMENT-PLATFORM-LEAD": ("comment", b"; NEC98 BIOS lead"),
        }
        by_id = {item["id"]: item for item in scanner.RULES}
        self.assertEqual(set(fixtures), set(by_id))
        for rule_id, (kind, fixture) in fixtures.items():
            rule = by_id[rule_id]
            value = fixture if kind == "path" else fixture
            if kind == "path":
                matched = scanner.match_path(rule, value)
            else:
                if kind == "comment":
                    self.assertTrue(scanner.comment_line(value))
                matched = re.search(rule["matcher"].encode("ascii"), value, re.I) is not None
            self.assertTrue(matched, rule_id)

    def test_scanner_is_repeatable_and_covers_required_surfaces(self):
        first = scanner.scan_repository(ROOT)
        second = scanner.scan_repository(ROOT)
        self.assertEqual(scanner.canonical_json_bytes(first), scanner.canonical_json_bytes(second))
        self.assertEqual(first["surface_coverage"], list(scanner.SURFACES))
        self.assertTrue(first["entries"])
        self.assertEqual({item["classification"] for item in first["entries"]}, {"OBSERVATION"})

    def test_canonical_json_has_one_final_newline(self):
        encoded = scanner.canonical_json_bytes({"b": 2, "a": "x"})
        self.assertTrue(encoded.endswith(b"\n"))
        self.assertFalse(encoded[:-1].endswith(b"\n"))
        self.assertEqual(encoded, b'{\n  "a": "x",\n  "b": 2\n}\n')


class VerifierFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.components = verifier.verify_baseline(ROOT)
        cls.data = scanner.scan_repository(ROOT)

    def invalid_data(self):
        return copy.deepcopy(self.data)

    def assert_invalid_entries(self, data):
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_entries(data, self.components)

    def test_duplicate_entry_id_is_rejected(self):
        data = self.invalid_data()
        data["entries"][1]["id"] = data["entries"][0]["id"]
        self.assert_invalid_entries(data)

    def test_missing_surface_is_rejected(self):
        data = self.invalid_data()
        data["surface_coverage"].remove("boot")
        self.assert_invalid_entries(data)

    def test_invalid_closed_vocabulary_is_rejected(self):
        data = self.invalid_data()
        data["entries"][0]["surface"] = "not-a-surface"
        self.assert_invalid_entries(data)

    def test_undocumented_rule_is_rejected(self):
        data = self.invalid_data()
        data["entries"][0]["matched_rule"] = "UNREGISTERED-RULE"
        self.assert_invalid_entries(data)

    def test_absolute_path_and_timestamp_are_rejected(self):
        absolute = self.invalid_data()
        absolute["entries"][0]["notes"] = "/tmp/host-dependent"
        self.assert_invalid_entries(absolute)
        timestamp = self.invalid_data()
        timestamp["entries"][0]["notes"] = "2026-08-30T12:00:00"
        self.assert_invalid_entries(timestamp)

    def test_document_fact_requires_register_and_page(self):
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_document_fact({"classification": "DOCUMENT_FACT"}, {"SRC-OK"})

    def test_pc88va_fact_cannot_use_pc98_only_material(self):
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_pc88va_support({"platform": "pc88va", "support_material": "pc98"})

    def test_resolved_blocker_requires_accepted_evidence(self):
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_blocker_records([{"question_id": "M04-X", "current_state": "RESOLVED", "accepted_evidence": ["UNKNOWN"]}])

    def test_unsafe_changed_paths_are_rejected(self):
        for path in ("docs/private/manual.md", "qa/results/m03/run.json", "output.bin", "components/pc88va/main.c"):
            with self.subTest(path=path), self.assertRaises(verifier.VerificationError):
                verifier.validate_changed_paths([path])

    def test_noncanonical_json_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_text('{"b": 2, "a": 1}\n', encoding="utf-8")
            with self.assertRaises(verifier.VerificationError):
                verifier.load_canonical(path)
            path.write_text('{"a": 1, "b": 2}', encoding="utf-8")
            with self.assertRaises(verifier.VerificationError):
                verifier.load_canonical(path)

    def test_ruleset_digest_is_stable(self):
        self.assertEqual(scanner.ruleset_sha256(), scanner.ruleset_sha256())
        self.assertEqual(len(scanner.ruleset_descriptors()), len(scanner.RULES))


if __name__ == "__main__":
    unittest.main()
