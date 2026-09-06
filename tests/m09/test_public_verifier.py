# SPDX-License-Identifier: GPL-2.0-or-later
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('m09_verifier', ROOT / 'tools/m09/verify_m09.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class VerifierTests(unittest.TestCase):
    def test_real_contract(self):
        MODULE.validate_contract(MODULE.json_file(ROOT/'config/m09/console-contract.json'))

    def test_acceptance_without_ci_rejected(self):
        data = MODULE.json_file(ROOT/'config/m09/console-contract.json')
        data.update(status='accepted', parent_ci=None)
        with self.assertRaises(MODULE.VerificationError):
            MODULE.validate_contract(data)

    def test_unknown_contract_field_rejected(self):
        data = MODULE.json_file(ROOT/'config/m09/console-contract.json')
        data['synthetic_private_value'] = 1
        with self.assertRaises(MODULE.VerificationError):
            MODULE.validate_contract(data)

    def test_missing_artifact_manifest_rejected(self):
        data = MODULE.json_file(ROOT/'config/m09/console-contract.json')
        del data['artifact_manifest']
        with self.assertRaises(MODULE.VerificationError):
            MODULE.validate_contract(data)

    def test_wrong_vaeg_rejected(self):
        data = MODULE.json_file(ROOT/'config/m09/console-contract.json')
        data['vaeg_commit'] = '0'*40
        with self.assertRaises(MODULE.VerificationError):
            MODULE.validate_contract(data)

    def test_failed_native_ci_rejected(self):
        data = MODULE.json_file(ROOT/'config/m09/console-contract.json')
        data.update(status='accepted', parent_ci={'commit':'1'*40,'run':1,'conclusion':'failure'})
        with self.assertRaises(MODULE.VerificationError):
            MODULE.validate_contract(data)

    def test_accepted_m08_records_unchanged(self):
        for path, expected in MODULE.ACCEPTED_M08.items():
            self.assertEqual(MODULE.sha(ROOT / path), expected)

    def test_real_schema_and_manifest(self):
        MODULE.validate_manifest(MODULE.json_file(ROOT / 'schema/m09-artifact-manifest.schema.json'),
                                 MODULE.json_file(ROOT / 'qa/golden/m09/manifest.json'))

    def test_instance_rejection_redacts_value(self):
        schema = MODULE.json_file(ROOT / 'schema/m09-artifact-manifest.schema.json')
        manifest = MODULE.json_file(ROOT / 'qa/golden/m09/manifest.json')
        manifest['artifacts']['kernel_sys']['sha256'] = 'synthetic-sensitive-identity'
        with self.assertRaises(MODULE.VerificationError) as raised:
            MODULE.validate_manifest(schema, manifest)
        self.assertNotIn('synthetic-sensitive-identity', str(raised.exception))

    def test_invalid_schema_rejected(self):
        with self.assertRaises(MODULE.VerificationError):
            MODULE.validate_manifest({'type': 'not-a-json-type'}, {})

    def test_digest_mismatch_rejected(self):
        with self.assertRaisesRegex(MODULE.VerificationError, 'digest mismatch'):
            MODULE.bound_record(ROOT, {'path': 'qa/golden/m09/manifest.json', 'sha256': '0'*64})

    def test_private_path_not_followed(self):
        for path in ('/synthetic-private-input.json', '../synthetic-private-input.json'):
            with self.assertRaisesRegex(MODULE.VerificationError, 'non-public'):
                MODULE.bound_record(ROOT, {'path': path, 'sha256': '0'*64})

    def test_reference_extra_field_rejected(self):
        with self.assertRaises(MODULE.VerificationError):
            MODULE.bound_record(ROOT, {'path': 'anything', 'sha256': '0'*64, 'private': 'synthetic'})

    def test_symlink_evidence_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'real.json').write_text('{}')
            (root/'link.json').symlink_to(root/'real.json')
            with self.assertRaises(MODULE.VerificationError):
                MODULE.json_file(root/'link.json')
