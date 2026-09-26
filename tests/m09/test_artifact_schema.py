# SPDX-License-Identifier: GPL-2.0-or-later
import copy
import json
from pathlib import Path
import unittest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


class SchemaTests(unittest.TestCase):
    def setUp(self):
        schema = json.loads((ROOT / 'schema/m09-artifact-manifest.schema.json').read_text())
        Draft202012Validator.check_schema(schema)
        self.validator = Draft202012Validator(schema)
        self.manifest = json.loads((ROOT / 'qa/golden/m09/manifest.json').read_text())

    def test_real_instance_conforms(self):
        self.validator.validate(self.manifest)

    def test_kernel_provenance_required(self):
        for key in ('compile_manifest_sha256', 'kernel_interface_sha256', 'symbol_evidence_sha256'):
            changed = copy.deepcopy(self.manifest)
            del changed['artifacts']['kernel_sys'][key]
            self.assertFalse(self.validator.is_valid(changed))

    def test_private_field_rejected(self):
        self.manifest['private_input'] = 'synthetic-private-value'
        self.assertFalse(self.validator.is_valid(self.manifest))

    def test_generic_provenance_rejected(self):
        self.manifest['artifacts']['raw_media']['compile_manifest_sha256'] = 'a' * 64
        self.assertFalse(self.validator.is_valid(self.manifest))

    def test_invalid_hash_rejected(self):
        for value in ('a' * 63, 'Z' * 64, 12, None):
            self.manifest['artifacts']['kernel_sys']['sha256'] = value
            self.assertFalse(self.validator.is_valid(self.manifest))

    def test_false_reproducibility_rejected(self):
        self.manifest['two_clean_builds_equal'] = False
        self.assertFalse(self.validator.is_valid(self.manifest))
