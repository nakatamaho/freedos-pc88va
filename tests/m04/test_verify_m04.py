#!/usr/bin/env python3
"""Positive and fail-closed fixtures for the provisional M04 contract."""

import copy
import json
import struct
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/m04"))

import verify_m04 as verifier  # noqa: E402


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def field(value, status="design_choice", confidence="high", claims=None, target="M05"):
    return {
        "claim_ids": sorted(claims or ["DEC-FAT12-LAYOUT"]),
        "confidence": confidence,
        "status": status,
        "validation_target": target,
        "value": value,
    }


def synthetic_d88(payload=b"A" * 128):
    header = bytearray(0x2B0)
    sector = bytearray(16) + bytearray(payload)
    sector[0:4] = bytes((0, 0, 1, 0))
    struct.pack_into("<H", sector, 4, 1)
    struct.pack_into("<H", sector, 14, len(payload))
    struct.pack_into("<I", header, 0x20, len(header))
    result = header + sector
    struct.pack_into("<I", result, 0x1C, len(result))
    return bytes(result)


class ContractPositiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load(verifier.CONTRACT_RELATIVE)
        cls.evidence = load(verifier.EVIDENCE_RELATIVE)
        cls.claim_ids = verifier.validate_evidence(cls.evidence)

    def test_public_contract_and_arithmetic_pass(self):
        verifier.validate_contract_data(copy.deepcopy(self.contract), self.claim_ids)

    def test_born_digital_and_markdown_locators_are_distinct(self):
        by_id = {item["claim_id"]: item for item in self.evidence["claims"]}
        born = by_id["TXT-FDD-2HD-GEOMETRY"]
        export = by_id["MD-IPL-STARTUP"]
        self.assertEqual(born["claim_type"], "electronic_document_fact")
        self.assertEqual(born["status"], "confirmed")
        self.assertEqual(export["claim_type"], "text_export_fact")
        self.assertEqual(export["status"], "supported")
        self.assertEqual(export["confidence"], "medium")

    def test_missing_image_reference_is_recorded_without_global_failure(self):
        self.assertEqual(verifier.count_image_references("diagram.gif"), 1)
        self.assertEqual(verifier.count_image_references("plain text"), 0)

    def test_unknowns_block_only_their_downstream_milestones(self):
        public = self.contract["readiness"]["public"]
        self.assertEqual(verifier.get_value(public, "M05"), "ready_with_assumptions")
        self.assertEqual(verifier.get_value(public, "M06"), "ready_with_assumptions")
        self.assertEqual(verifier.get_value(public, "M07"), "blocked")
        self.assertEqual(verifier.get_value(public, "M08"), "blocked")

    def test_timer_and_keyboard_are_deferred(self):
        dispositions = {item["question_id"]: verifier.get_value(item, "disposition") for item in self.contract["blocker_dispositions"]}
        self.assertEqual(dispositions["M04-BOOT-TIMER"], "deferred_m10")
        self.assertEqual(dispositions["M04-KEYBOARD-ENCODING"], "deferred_m11")

    def test_trace_only_is_not_console_support(self):
        self.assertEqual(verifier.get_value(self.contract["early_diagnostics"], "m07_strategy"), "trace_only_candidate")
        self.assertEqual(verifier.get_value(self.contract["early_diagnostics"], "full_console"), "deferred_to_M09")

    def test_kernel_identity_is_role_only(self):
        role = self.contract["kernel_payload_role"]
        self.assertEqual(verifier.get_value(role, "accepted_baseline_size"), 83774)
        self.assertIn("nec98_baseline", verifier.get_value(role, "baseline_platform"))
        self.assertIn("future_M06", verifier.get_value(role, "payload_source"))

    def test_synthetic_d88_parser_accepts_bounded_fixture(self):
        self.assertEqual(verifier.parse_synthetic_d88(synthetic_d88()), [(0, 0, 1, 0, 128)])

    def test_redacted_private_observation_has_no_value(self):
        record = self.contract["firmware_dependency"]["private_observation"]
        self.assertIsNone(record["value"])
        self.assertEqual(record["status"], "private_observation")

    def test_fictional_private_overlay_is_deterministic(self):
        overlay = {"claim_ids": ["FICTIONAL-01"], "values": {"sector": 7}}
        self.assertEqual(verifier.canonical_json_bytes(overlay), verifier.canonical_json_bytes(copy.deepcopy(overlay)))


class ContractNegativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load(verifier.CONTRACT_RELATIVE)
        cls.evidence = load(verifier.EVIDENCE_RELATIVE)
        cls.claim_ids = verifier.validate_evidence(cls.evidence)

    def invalid(self):
        return copy.deepcopy(self.contract)

    def reject(self, data):
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_contract_data(data, self.claim_ids)

    def test_hardware_value_without_claim_is_rejected(self):
        data = self.invalid()
        data["selected_candidate_medium"]["bytes_per_sector"]["claim_ids"] = []
        self.reject(data)

    def test_confirmed_uncorroborated_text_export_is_rejected(self):
        evidence = copy.deepcopy(self.evidence)
        item = next(x for x in evidence["claims"] if x["claim_id"] == "MD-IPL-STARTUP")
        item["status"] = "confirmed"
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_evidence(evidence)

    def test_working_assumption_without_target_is_rejected(self):
        data = self.invalid()
        data["preferred_disk_access"]["candidate"]["validation_target"] = ""
        self.reject(data)

    def test_unknown_without_downstream_impact_is_rejected(self):
        data = self.invalid()
        data["boot_record"]["signature"]["validation_target"] = ""
        self.reject(data)

    def test_private_observation_exposing_value_is_rejected(self):
        data = self.invalid()
        data["firmware_dependency"]["private_observation"]["value"] = 4660
        self.reject(data)

    def test_private_binary_markers_are_rejected(self):
        markers = (
            "/private/local/source", "pc88va-private-docs", "sample.d88",
            "sample.rom", "ROM string", "disassembly dump", "private hash",
        )
        for marker in markers:
            with self.subTest(marker=marker), self.assertRaises(verifier.VerificationError):
                verifier.reject_private_text(marker)

    def test_known_bad_dump_name_is_rejected(self):
        with self.assertRaises(verifier.VerificationError):
            verifier.reject_private_text("varom00_mame_baddump.rom")

    def test_va_and_va2_observations_cannot_be_merged(self):
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_model_observations([{"models": ["va", "va2"]}])

    def test_first_d88_sector_boot_assumption_requires_support(self):
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_boot_candidate_support({"assumes_first_physical_sector": True, "txt_or_rom_claim_ids": []})

    def test_truncated_and_out_of_bounds_d88_are_rejected(self):
        with self.assertRaises(verifier.VerificationError):
            verifier.parse_synthetic_d88(b"short")
        broken = bytearray(synthetic_d88())
        struct.pack_into("<I", broken, 0x1C, len(broken) + 1)
        with self.assertRaises(verifier.VerificationError):
            verifier.parse_synthetic_d88(bytes(broken))

    def test_private_input_mutation_is_rejected(self):
        with self.assertRaises(verifier.VerificationError):
            verifier.verify_input_preservation(b"fictional before", b"fictional after")

    def test_m05_readiness_requires_evaluable_invariants(self):
        data = self.invalid()
        next(x for x in data["derived_invariants"] if x["name"] == "fat12_capacity")["status"] = "not_evaluable"
        self.reject(data)

    def test_media_and_fat_arithmetic_mismatches_are_rejected(self):
        media = self.invalid()
        media["selected_candidate_medium"]["total_bytes"]["value"] += 1
        self.reject(media)
        fat = self.invalid()
        fat["filesystem"]["sectors_per_fat"]["value"] = 1
        self.reject(fat)

    def test_invalid_chs_sector_base_is_rejected(self):
        data = self.invalid()
        data["addressing"]["physical_sector_id_base"]["value"] = 0
        self.reject(data)

    def test_integer_hex_mismatch_is_rejected(self):
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_integer_hex(1024, "0200")

    def test_nec98_boot_artifact_cannot_be_a_va_fact(self):
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_pc88va_source("nec98")
        with self.assertRaises(verifier.VerificationError):
            verifier.reject_private_text("private/sample.rom")

    def test_component_and_baseline_paths_are_rejected(self):
        for path in (
            "components/fdkernel", "manifests/components.lock.json",
            "qa/golden/m03/port-surface.json", "qa/results/m04/output.json",
            "output.bin", "image.img", "archive.tar",
        ):
            with self.subTest(path=path), self.assertRaises(verifier.VerificationError):
                verifier.validate_changed_paths([path])

    def test_exact_m03_verifier_portability_fix_is_allowed(self):
        verifier.validate_changed_paths(["tools/m03/verify_m03.py"])
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_changed_paths(["tools/m03/scan_port_surface.py"])

    def test_m04r1_license_paths_are_narrowly_allowed(self):
        verifier.validate_changed_paths([
            ".github/workflows/m04r1-license.yml",
            "COPYING",
            "LICENSE.md",
            "docs/licensing/README.md",
            "manifests/licenses.yml",
            "tests/qa/test_verify_license_policy.py",
            "tools/qa/verify_license_policy.py",
        ])
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_changed_paths(["manifests/components.lock.json"])

    def test_m05_parent_only_paths_are_narrowly_allowed(self):
        verifier.validate_changed_paths([
            ".github/workflows/m05-media.yml",
            "config/m05/media.json",
            "docs/porting/m05-media-image.md",
            "qa/golden/m05-media-manifest.json",
            "tests/m05/test_media.py",
            "tools/m05/build_media.py",
        ])
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_changed_paths(["components/fdkernel"])

    def test_m07r1_descendant_paths_are_narrowly_allowed(self):
        verifier.validate_changed_paths([
            "docs/porting/m07r1-production-trace-rerun.md",
            "schema/m07r1-public-status.schema.json",
        ], m06_active=True)
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_changed_paths([
                "docs/porting/m07r1-unreviewed-result.md",
            ], m06_active=True)

    def test_m08r2_evidence_paths_are_exact(self):
        paths = ["qa/golden/m08-artifact-manifest.json", "qa/golden/m08-golden.json",
                 "docs/porting/m08r2-report.md"]
        verifier.validate_changed_paths(paths, m06_active=True)
        for path in ("qa/golden/m08-unreviewed.json", "docs/porting/m08r2-unreviewed.md"):
            with self.assertRaises(verifier.VerificationError):
                verifier.validate_changed_paths([path], m06_active=True)

    def test_m07r2_descendant_paths_are_narrowly_allowed(self):
        verifier.validate_changed_paths([
            ".github/workflows/m07-probe.yml",
            "config/m07/m07r2-public-status.json",
            "docs/porting/m07r2-positive-control-diagnosis.md",
            "qa/golden/m07r2-public-status.sha256",
            "schema/m07r2-public-status.schema.json",
            "tests/m07r2/test_m07r2.py",
            "tools/m07r2/verify_m07r2.py",
        ], m06_active=True)
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_changed_paths([
                "docs/porting/m07r2-unreviewed-private-result.md",
            ], m06_active=True)

    def test_m07r4_descendant_paths_are_narrowly_allowed(self):
        verifier.validate_changed_paths([
            "config/m07/m07r4-public-status.json",
            "docs/porting/m07r4-rom-d88-reconstruction.md",
            "qa/golden/m07r4-public-status.sha256",
            "schema/m07r4-public-status.schema.json",
            "tools/m07/verify_m07r4.py",
        ], m06_active=True)
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_changed_paths([
                "docs/porting/m07r4-private-result.md",
            ], m06_active=True)

    def test_m07_completion_paths_are_narrowly_allowed(self):
        verifier.validate_changed_paths([
            ".github/workflows/m07-completion.yml",
            "config/m07/m07-completion-public-status.json",
            "docs/porting/m07-report.md",
            "qa/golden/m07-completion-public-status.sha256",
            "schema/m07-completion-public-status.schema.json",
            "tests/m07/test_m07_completion.py",
            "tools/m07/verify_m07_completion.py",
        ], m06_active=True)
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_changed_paths([
                "qa/golden/m07-private-result.json",
            ], m06_active=True)

    def test_component_gitlink_drift_is_rejected(self):
        data = self.invalid()
        data["component_gitlinks"]["fdkernel"] = "0" * 40
        self.reject(data)

    def test_consumed_m01_m03_identity_drift_is_rejected(self):
        data = self.invalid()
        data["consumed_identities"]["m03r1_golden_sha256"] = "0" * 64
        self.reject(data)

    def test_ci_cannot_claim_private_content_validation(self):
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_ci_boundary("CI inspected private source contents")

    def test_timestamp_and_host_path_are_rejected(self):
        data = self.invalid()
        data["open_questions"][0]["timestamp"] = "2026-08-31T10:00:00"
        self.reject(data)


if __name__ == "__main__":
    unittest.main()
