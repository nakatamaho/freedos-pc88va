# SPDX-License-Identifier: GPL-2.0-or-later
"""Keep the M15 FreeDOS/VA service boundary finite and explicit."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/m15"))
from verify_api_inventory_scope import INVENTORY, verify


class ApiInventoryScopeTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(INVENTORY.read_text(encoding="utf-8"))

    def test_locked_boundary_and_six_separate_reference_questions_pass(self):
        result = verify(self.data)
        self.assertEqual((result["rows"], result["required_services"],
                          result["deferred_reference_questions"]), (221, 113, 6))

    def test_target_change_or_added_dispatch_entry_is_rejected(self):
        changed_target = copy.deepcopy(self.data)
        changed_target["scope_lock"]["target"] += "; MS-DOS exact match"
        with self.assertRaises(ValueError):
            verify(changed_target)

        added = copy.deepcopy(self.data)
        added["rows"].append(copy.deepcopy(added["rows"][0]))
        with self.assertRaises(ValueError):
            verify(added)

    def test_source_identity_and_port_boundary_language_are_locked(self):
        changed_source = copy.deepcopy(self.data)
        changed_source["source_baseline"]["fdkernel"] = "0" * 40
        with self.assertRaises(ValueError):
            verify(changed_source)

        changed_scope = copy.deepcopy(self.data)
        changed_scope["scope_lock"]["membership_rule"] = "MS-DOS behavior must match exactly"
        with self.assertRaises(ValueError):
            verify(changed_scope)

        changed_row = copy.deepcopy(self.data)
        changed_row["rows"][0]["contract_status"] = changed_row["rows"][0].pop("port_review_status")
        with self.assertRaises(ValueError):
            verify(changed_row)

        changed_format = copy.deepcopy(self.data)
        changed_format["format_version"] = 1
        with self.assertRaises(ValueError):
            verify(changed_format)

    def test_private_per_case_results_are_not_part_of_the_public_ledger(self):
        changed = copy.deepcopy(self.data)
        changed["rows"][0]["outcome"] = "PASS"
        with self.assertRaises(ValueError):
            verify(changed)

        changed = copy.deepcopy(self.data)
        changed["rows"][0]["observation_record"] = "per-case observation"
        with self.assertRaises(ValueError):
            verify(changed)

    def test_deferred_reference_question_requires_parent_issue_and_not_run(self):
        for field, value in (("issue", ""), ("outcome", "PASS"),
                             ("status", "REQUIRED")):
            changed = copy.deepcopy(self.data)
            row = next(row for row in changed["rows"]
                       if row["id"] == "21-3A")
            row["deferred_reference_review"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify(changed)


if __name__ == "__main__":
    unittest.main()
