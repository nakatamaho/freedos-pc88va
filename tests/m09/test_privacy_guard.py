# SPDX-License-Identifier: GPL-2.0-or-later
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('privacy', ROOT/'tools/m09/privacy_guard.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PrivacyTests(unittest.TestCase):
    def test_public_text(self):
        MODULE.check_blob('docs/report.md', b'Private gate performed; hardware not run.')

    def test_generated_artifact(self):
        with self.assertRaises(ValueError):
            MODULE.check_blob('output.d88', b'synthetic')

    def test_binary_disguised_as_json(self):
        with self.assertRaises(ValueError):
            MODULE.check_blob('output.json', b'MZsynthetic')

    def test_local_path(self):
        with self.assertRaises(ValueError):
            MODULE.check_blob('report.md', b'/' + b'Users/synthetic/data')

    def test_registered_identity(self):
        with self.assertRaises(ValueError):
            MODULE.check_blob('report.md', b'synthetic-secret', (b'synthetic-secret',))

    def test_private_evidence_location(self):
        with self.assertRaises(ValueError):
            MODULE.check_blob('.private-evidence/result.json', b'{}')
