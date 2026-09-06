# SPDX-License-Identifier: GPL-2.0-or-later
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('scope', ROOT/'tools/qa/m09_scope.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ScopeTests(unittest.TestCase):
    def test_source_allowed(self):
        self.assertTrue(MODULE.is_public_m09_path('tools/m09/verify_m09.py'))

    def test_binary_rejected(self):
        for suffix in ('rom', 'bin', 'd88', 'img', 'log', 'tar', 'trace'):
            self.assertFalse(MODULE.is_public_m09_path('tools/m09/output.'+suffix))

    def test_unrelated_evidence_rejected(self):
        self.assertFalse(MODULE.is_public_m09_path('qa/golden/m08-artifact-manifest.json'))

    def test_traversal_rejected(self):
        self.assertFalse(MODULE.is_public_m09_path('tools/m09/../../private.py'))
