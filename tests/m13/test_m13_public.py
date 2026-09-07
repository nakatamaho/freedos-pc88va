#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
import copy, json, unittest
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]

class M13PublicTests(unittest.TestCase):
    def test_actual_contract_instances(self):
        for name in ("machine-contract", "integration-contract"):
            schema = json.loads((ROOT / f"schema/m13-{name}.schema.json").read_text())
            Draft202012Validator.check_schema(schema)
            instance = json.loads((ROOT / f"config/m13/{name}.json").read_text())
            Draft202012Validator(schema).validate(instance)
        import sys
        sys.path.insert(0, str(ROOT / "tools/m13"))
        import verify_m13
        verify_m13.content()
        verify_m13.sources()

    def test_schema_rejects_unknown_and_missing_fields(self):
        schema = json.loads((ROOT / "schema/m13-integration-contract.schema.json").read_text())
        value = json.loads((ROOT / "config/m13/integration-contract.json").read_text())
        bad = copy.deepcopy(value); bad["unexpected"] = True
        with self.assertRaises(Exception): Draft202012Validator(schema).validate(bad)
        bad = copy.deepcopy(value); del bad["startup"]
        with self.assertRaises(Exception): Draft202012Validator(schema).validate(bad)

    def test_common_core_and_real_adapter_are_selected(self):
        plan = json.loads((ROOT / "components/fdkernel/pc88va/config/m13-build-plan.json").read_text())
        sources = {x["source"] for x in plan["objects"] if x["classification"] == "common-core"}
        for path in ("kernel/main.c", "kernel/inthndlr.c", "kernel/fatfs.c", "kernel/memmgr.c", "kernel/task.c", "kernel/procsupt.asm"):
            self.assertIn(path, sources)
        adapter = (ROOT / "components/fdkernel/pc88va/kernel/m13_platform.asm").read_text()
        self.assertIn("pc88va_kernel_disk_read_", adapter)
        self.assertIn("reject_word FL_WRITE", adapter)

    def test_guest_probes_use_dos_interrupts(self):
        com = (ROOT / "tests/m13/fixtures/com_probe.asm").read_text()
        mz = (ROOT / "tests/m13/fixtures/mz_probe.asm").read_text()
        self.assertIn("int 21h", com); self.assertIn("int 21h", mz)
        self.assertNotIn("pc88va_", com + mz)

if __name__ == "__main__":
    unittest.main()
