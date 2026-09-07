#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Fail-closed parent tests for the M06 compile-only kernel target."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("m06_harness", ROOT / "tools/m06/m06.py")
assert SPEC and SPEC.loader
M06 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M06)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class M06Tests(unittest.TestCase):
    def test_current_lock_separates_historical_and_current_identity(self) -> None:
        lock = M06.load_json(ROOT / M06.CURRENT_LOCK)
        M06.validate_current_lock(lock)
        self.assertEqual(lock["historical_components_lock"]["sha256"], M06.IDENTITIES["components_lock"][1])
        current = {item["path"]: item["commit"] for item in lock["components"]}
        self.assertEqual(current, M06.EXPECTED_GITLINKS)
        self.assertNotEqual(current["components/fdkernel"], M06.PC88VA_PARENT)

    def test_tampered_current_lock_is_rejected(self) -> None:
        lock = copy.deepcopy(M06.load_json(ROOT / M06.CURRENT_LOCK))
        lock["components"][0]["commit"] = M06.PC88VA_PARENT
        with self.assertRaises(M06.M06Error):
            M06.validate_current_lock(lock)

    def test_historical_and_contract_identities_are_preserved(self) -> None:
        for _, (relative, expected) in M06.IDENTITIES.items():
            self.assertEqual(sha256(ROOT / relative), expected, relative)

    def test_component_gitlinks_are_exact_and_clean(self) -> None:
        M06.validate_component_state(require_remote=False)

    def test_child_lineage_and_source_archive_are_exact(self) -> None:
        component = ROOT / "components/fdkernel"
        self.assertEqual(
            subprocess.run(
                ["git", "merge-base", "--is-ancestor", M06.PC88VA_PARENT, M06.PC88VA_COMMIT],
                cwd=component,
                check=False,
            ).returncode,
            0,
        )
        first = subprocess.check_output(
            ["git", "rev-list", "--reverse", f"{M06.PC88VA_PARENT}..{M06.PC88VA_COMMIT}"],
            cwd=component,
            text=True,
        ).splitlines()[0]
        self.assertEqual(subprocess.check_output(["git", "rev-parse", f"{first}^"], cwd=component, text=True).strip(), M06.PC88VA_PARENT)
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(
                M06.identity(M06.create_source_archive(Path(temporary)))["sha256"],
                M06.SOURCE_ARCHIVE_SHA256,
            )

    def test_m05_boot_signature_and_timestamp_regression(self) -> None:
        M06.validate_m05_regression()
        raw = (ROOT / "qa/results/m05/run-1/pc88va-m05-candidate.img").read_bytes()
        self.assertNotEqual(raw[510:512], b"\x55\xaa")
        self.assertNotEqual(raw[1022:1024], b"\x55\xaa")

    def test_pc88va_kernel_and_media_extraction_match(self) -> None:
        run = ROOT / "qa/results/m06/run-1"
        kernel = M06.identity(run / "kernel/compiled/KERNEL.SYS")
        M06.validate_kernel_role(kernel)
        self.assertEqual(M06.identity(run / "media/extracted/KERNEL.SYS"), kernel)
        self.assertNotEqual(kernel["sha256"], M06.OLD_KERNEL_SHA256)

    def test_old_nec98_kernel_cannot_fill_pc88va_role(self) -> None:
        with self.assertRaises(M06.M06Error):
            M06.validate_kernel_role({"sha256": M06.OLD_KERNEL_SHA256, "size": 83774})

    def test_m06_records_reject_old_nec98_kernel(self) -> None:
        old = ROOT / "qa/results/m06/run-1/kernel/nec98/kernel.sys"
        with self.assertRaises(M06.M06Error):
            M06.m06_records(old)

    def test_stub_ledger_matches_source_and_symbols(self) -> None:
        ledger = M06.load_json(ROOT / "components/fdkernel/pc88va/config/stubs.json")
        source = (ROOT / "components/fdkernel/pc88va/kernel/stubs.c").read_text(encoding="utf-8")
        M06.validate_stub_ledger(ledger, source)
        symbols = M06.load_json(ROOT / "qa/results/m06/run-1/kernel/evidence/symbol-evidence.json")
        names = {item["name"] for item in symbols["symbols"]}
        self.assertTrue({f"{item['name']}_" for item in ledger["interfaces"]}.issubset(names))

    def test_missing_stub_is_rejected(self) -> None:
        ledger = copy.deepcopy(M06.load_json(ROOT / "components/fdkernel/pc88va/config/stubs.json"))
        ledger["interfaces"].pop()
        source = (ROOT / "components/fdkernel/pc88va/kernel/stubs.c").read_text(encoding="utf-8")
        with self.assertRaises(M06.M06Error):
            M06.validate_stub_ledger(ledger, source)

    def test_compile_manifest_has_explicit_independent_link_order(self) -> None:
        manifest = M06.load_json(ROOT / "qa/results/m06/run-1/kernel/evidence/compile-manifest.json")
        self.assertEqual(manifest["target_macros"], ["DBCS", "JAPAN", "PC88VA"])
        self.assertEqual(manifest["link_inputs_in_order"], ["pc88va/build/startup.obj", "pc88va/build/platform.lib"])
        self.assertFalse(any("nec98" in item["source"].lower() for item in manifest["objects"]))

    def test_nec98_regression_is_exact(self) -> None:
        contract = M06.load_json(ROOT / M06.CONTRACT)
        self.assertEqual(len(M06.validate_nec98(ROOT / "qa/results/m06/run-1", contract)), 8)
        self.assertEqual(len(M06.validate_nec98(ROOT / "qa/results/m06/run-2", contract)), 8)

    def test_unchanged_media_payloads_are_exact(self) -> None:
        inspection = M06.load_json(ROOT / "qa/results/m06/run-1/media/inspection-manifest.json")
        payloads = {item["dos_name"]: (item["size"], item["sha256"]) for item in inspection["extracted_payloads"]}
        for name, expected in M06.EXPECTED_UNCHANGED_PAYLOADS.items():
            self.assertEqual(payloads[name], expected)

    def test_raw_d88_round_trip_and_two_runs(self) -> None:
        recorded = M06.load_json(ROOT / "qa/results/m06/comparison.json")
        self.assertEqual(recorded, M06.compare_runs(write=False))
        self.assertTrue(recorded["byte_identical"])
        contract = M06.load_json(ROOT / M06.CONTRACT)
        M06.verify_run(ROOT / "qa/results/m06/run-1", contract)

    def test_kernel_interface_schema_matches_artifact(self) -> None:
        interface = M06.load_json(ROOT / "qa/results/m06/run-1/kernel/evidence/kernel-interface.json")
        M06.validate_interface_schema(interface)
        self.assertEqual(interface["physical_load_address"]["status"], "unknown")
        self.assertEqual(interface["firmware_entry_state"]["status"], "unknown")

    def test_generated_and_private_outputs_are_not_tracked(self) -> None:
        M06.validate_tracked_safety()

    def test_root_license_policy_still_passes(self) -> None:
        result = subprocess.run(
            ["python3", "tools/qa/verify_license_policy.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
