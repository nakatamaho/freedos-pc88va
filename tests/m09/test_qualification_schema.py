# SPDX-License-Identifier: GPL-2.0-or-later
import copy
import json
from pathlib import Path
import unittest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


class QualificationTests(unittest.TestCase):
    def setUp(self):
        schema = json.loads((ROOT/'schema/m09-public-qualification.schema.json').read_text())
        Draft202012Validator.check_schema(schema)
        self.validator = Draft202012Validator(schema)
        run = dict(console_boundaries=['C'+str(n) for n in range(10)],
                   loader_boundaries=['L'+str(n) for n in range(10)],
                   exact_guest_message=True, cursor_CR_LF_wrap=True, bottom_row_policy=True,
                   ownership_preserved=True, inputs_preserved=True,
                   firmware_operational_state_restored=True, no_unexpected_disk_keyboard_clock_DMA=True)
        self.fixture = dict(schema_version=1, child_commit='a'*40,
                            vaeg_commit='7463f9501d84701f50f3243d5067b6a9dfd0c2e7', kernel_sha256='b'*64,
                            private_gate='performed', runs=[copy.deepcopy(run),copy.deepcopy(run)],
                            two_clean_runs_equal=True, evidence_retention='persistent_ignored',
                            public_promotion_status='prohibited_pending_user_approval',
                            hardware_run=False, private_gate_in_public_ci=False)

    def test_synthetic_complete_record(self):
        self.validator.validate(self.fixture)

    def test_missing_console_boundary(self):
        self.fixture['runs'][0]['console_boundaries'].pop()
        self.assertFalse(self.validator.is_valid(self.fixture))

    def test_loader_regression_cannot_be_skipped(self):
        self.fixture['runs'][1]['loader_boundaries'] = []
        self.assertFalse(self.validator.is_valid(self.fixture))

    def test_single_run_cannot_pass(self):
        self.fixture['runs'].pop()
        self.assertFalse(self.validator.is_valid(self.fixture))

    def test_false_preservation_cannot_pass(self):
        self.fixture['runs'][0]['inputs_preserved'] = False
        self.assertFalse(self.validator.is_valid(self.fixture))

    def test_private_value_rejected(self):
        self.fixture['runs'][0]['load_address'] = 1234
        self.assertFalse(self.validator.is_valid(self.fixture))

    def test_private_hash_rejected(self):
        self.fixture['private_projection_sha256'] = 'c'*64
        self.assertFalse(self.validator.is_valid(self.fixture))

    def test_public_ci_cannot_claim_private_run(self):
        self.fixture['private_gate_in_public_ci'] = True
        self.assertFalse(self.validator.is_valid(self.fixture))
