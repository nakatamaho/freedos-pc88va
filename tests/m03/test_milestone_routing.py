#!/usr/bin/env python3
"""Positive and fail-closed fixtures for M03R1 milestone routing."""

import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/m03"))

import scan_port_surface as scanner  # noqa: E402
import verify_m03 as verifier  # noqa: E402


def observation(surface, path, token, component="fdkernel", mechanism="function_boundary"):
    return {
        "id": "0123456789abcdef",
        "component": component,
        "component_commit": "0" * 40,
        "platform": "shared",
        "path": path,
        "symbol_or_section": "fixture_symbol",
        "surface": surface,
        "mechanism": mechanism,
        "matched_rule": "FIXTURE-RULE",
        "evidence_excerpt_or_token": token,
        "classification": "OBSERVATION",
        "candidate_boundary": "fixture boundary",
        "disposition": "investigate",
        "confidence": "high",
        "notes": "Newly authored routing fixture.",
    }


class RoutingPositiveFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = scanner.load_routing_policy(ROOT)

    def route(self, surface, path, token, component="fdkernel", mechanism="function_boundary"):
        return scanner.route_observation(observation(surface, path, token, component, mechanism), self.policy)

    def assert_route(self, routing, contract, implementation, status=None):
        self.assertEqual(routing["contract_milestones"], contract)
        self.assertEqual(routing["implementation_milestones"], implementation)
        if status is not None:
            self.assertEqual(routing["status"], status)

    def test_boot_sector_layout_routes_contract_and_image_assembly(self):
        routing = self.route("boot", "components/fdkernel/boot/layout.asm", "boot sector BPB FAT12")
        self.assert_route(routing, ["M04"], ["M05"], "curated")

    def test_ipl_entry_routes_contract_and_first_instruction(self):
        routing = self.route("boot", "components/fdkernel/boot/ipl.asm", "IPL real_start")
        self.assert_route(routing, ["M04"], ["M07"], "curated")

    def test_loader_disk_read_routes_contract_and_loader(self):
        routing = self.route("disk", "components/fdkernel/boot/read.asm", "readDisk sector")
        self.assert_route(routing, ["M04"], ["M08"], "curated")

    def test_kernel_floppy_read_routes_contract_and_read_only_driver(self):
        routing = self.route("disk", "components/fdkernel/drivers/floppy.asm", "FDC read sector")
        self.assert_route(routing, ["M04"], ["M12"], "curated")

    def test_floppy_write_and_media_change_route_to_m14(self):
        routing = self.route("disk", "components/fdkernel/drivers/floppy.asm", "write media-change")
        self.assert_route(routing, ["M04"], ["M14"], "curated")

    def test_console_output_and_japanese_output_routes(self):
        general = self.route("console_output", "components/fdkernel/console.c", "display")
        japanese = self.route("console_output", "components/fdkernel/console.c", "Japanese glyph")
        self.assert_route(general, [], ["M09"], "coarse")
        self.assert_route(japanese, [], ["M09", "M16"], "curated")

    def test_keyboard_and_japanese_input_routes(self):
        general = self.route("console_input", "components/fdkernel/keyboard.c", "keyboard")
        japanese = self.route("console_input", "components/fdkernel/keyboard.c", "Japanese filename")
        self.assert_route(general, [], ["M11"], "coarse")
        self.assert_route(japanese, [], ["M11", "M17"], "curated")

    def test_dbcs_compile_conditional_routes_only_to_m06(self):
        routing = self.route("nls_dbcs", "components/freecom/config.std", "DBCS", "freecom", "data_table")
        self.assert_route(routing, [], ["M06"], "curated")

    def test_command_exec_routes_to_read_only_session(self):
        routing = self.route("exec_runtime", "components/freecom/shell/command.c", "COMMAND EXEC", "freecom")
        self.assert_route(routing, [], ["M13"], "coarse")

    def test_write_command_routes_to_writable_session(self):
        routing = self.route("exec_runtime", "components/freecom/cmd/copy.c", "write command", "freecom")
        self.assert_route(routing, [], ["M15"], "curated")

    def test_explicit_scsi_path_routes_to_optional_hdd_extension(self):
        routing = self.route("disk", "components/fdkernel/drivers/scsi.c", "SCSI HDD")
        self.assert_route(routing, ["M04"], ["M18"], "curated")

    def test_unknown_surface_remains_unresolved(self):
        routing = self.route("unknown", "components/fdkernel/comment.asm", "BIOS comment")
        self.assert_route(routing, [], [], "unresolved")


class RoutingNegativeFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = scanner.load_routing_policy(ROOT)

    def routed(self, surface, path, token, component="fdkernel"):
        entry = observation(surface, path, token, component)
        entry["routing"] = scanner.route_observation(entry, self.policy)
        return entry

    def assert_routing_rejected(self, entry):
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_routing(entry, self.policy)

    def test_scalar_target_milestone_is_rejected(self):
        entry = self.routed("build", "components/fdkernel/makefile", "compiler")
        entry["target_milestone"] = "M06"
        self.assert_routing_rejected(entry)

    def test_generic_build_cannot_default_to_m05(self):
        entry = self.routed("build", "components/fdkernel/makefile", "compiler")
        entry["routing"]["implementation_milestones"] = ["M05"]
        self.assert_routing_rejected(entry)

    def test_general_console_output_cannot_default_to_m07(self):
        entry = self.routed("console_output", "components/fdkernel/console.c", "display")
        entry["routing"]["implementation_milestones"] = ["M07"]
        self.assert_routing_rejected(entry)

    def test_general_console_input_cannot_default_to_m08(self):
        entry = self.routed("console_input", "components/fdkernel/keyboard.c", "keyboard")
        entry["routing"]["implementation_milestones"] = ["M08"]
        self.assert_routing_rejected(entry)

    def test_general_exec_cannot_default_to_m11(self):
        entry = self.routed("exec_runtime", "components/freecom/shell/command.c", "EXEC", "freecom")
        entry["routing"]["implementation_milestones"] = ["M11"]
        self.assert_routing_rejected(entry)

    def test_generic_nls_cannot_be_reduced_to_m06(self):
        entry = self.routed("nls_dbcs", "components/country/country.asm", "DBCS", "country")
        entry["routing"]["implementation_milestones"] = ["M06"]
        self.assert_routing_rejected(entry)

    def test_unknown_cannot_route_to_m18(self):
        entry = self.routed("unknown", "components/fdkernel/comment.asm", "SCSI comment")
        entry["routing"]["status"] = "curated"
        entry["routing"]["implementation_milestones"] = ["M18"]
        entry["routing"]["rule_ids"] = ["route-explicit-hdd-extension"]
        self.assert_routing_rejected(entry)

    def test_m18_requires_explicit_hdd_rule(self):
        entry = self.routed("disk", "components/fdkernel/disk.c", "disk")
        entry["routing"]["implementation_milestones"] = ["M18"]
        self.assert_routing_rejected(entry)

    def test_nonempty_milestones_require_rule_id(self):
        entry = self.routed("build", "components/fdkernel/makefile", "compiler")
        entry["routing"]["rule_ids"] = []
        self.assert_routing_rejected(entry)

    def test_duplicate_and_unsorted_milestones_are_rejected(self):
        duplicate = self.routed("console_output", "components/fdkernel/console.c", "Japanese glyph")
        duplicate["routing"]["implementation_milestones"] = ["M09", "M09"]
        self.assert_routing_rejected(duplicate)
        unsorted = self.routed("console_output", "components/fdkernel/console.c", "Japanese glyph")
        unsorted["routing"]["implementation_milestones"] = ["M16", "M09"]
        self.assert_routing_rejected(unsorted)

    def test_milestone_outside_m04_m19_is_rejected(self):
        entry = self.routed("build", "components/fdkernel/makefile", "compiler")
        entry["routing"]["implementation_milestones"] = ["M20"]
        self.assert_routing_rejected(entry)

    def test_contract_only_m04_cannot_be_implementation(self):
        entry = self.routed("firmware", "components/fdkernel/bios.asm", "BIOS")
        entry["routing"]["implementation_milestones"] = ["M04"]
        self.assert_routing_rejected(entry)

    def test_undefined_policy_rule_is_rejected(self):
        entry = self.routed("build", "components/fdkernel/makefile", "compiler")
        entry["routing"]["rule_ids"] = ["route-missing"]
        self.assert_routing_rejected(entry)

    def test_generic_firmware_cannot_broadcast_to_implementation_stages(self):
        entry = self.routed("firmware", "components/fdkernel/bios.asm", "BIOS")
        entry["routing"]["implementation_milestones"] = ["M07", "M08", "M09", "M10", "M11", "M12", "M13", "M14"]
        self.assert_routing_rejected(entry)

    def test_membership_counts_cannot_claim_exclusive_partition(self):
        with self.assertRaises(verifier.VerificationError):
            verifier.validate_membership_count_semantics("Exclusive milestone partition")

    def test_component_evidence_and_private_paths_are_rejected(self):
        for path in (
            "components/fdkernel/kernel/new.c",
            "manifests/components.lock.json",
            "qa/golden/m02/bundle-manifest.json",
            "docs/private/manual.md",
            "qa/results/m03/output.json",
            "payload.rom",
            "kernel.obj",
            "bundle.tar",
        ):
            with self.subTest(path=path), self.assertRaises(verifier.VerificationError):
                if path.startswith(("components/", "manifests/", "qa/golden/m02/")):
                    verifier.validate_m03r1_changed_paths([path])
                else:
                    verifier.validate_changed_paths([path])

    def test_every_machine_policy_rule_requires_human_documentation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            document = root / verifier.ROUTING_POLICY_DOCUMENT
            document.parent.mkdir(parents=True)
            documented = self.policy["rules"][:-1]
            document.write_text("\n".join(f"`{item['id']}`" for item in documented) + "\n", encoding="utf-8")
            with self.assertRaises(verifier.VerificationError):
                verifier.validate_routing_policy_documentation(root, self.policy)


if __name__ == "__main__":
    unittest.main()
