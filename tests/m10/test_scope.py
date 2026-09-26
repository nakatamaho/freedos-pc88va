# SPDX-License-Identifier: GPL-2.0-or-later
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('scope',ROOT/'tools/qa/m10_scope.py')
scope=importlib.util.module_from_spec(spec);spec.loader.exec_module(scope)


class ScopeTests(unittest.TestCase):
    def test_public_m10_paths(self):
        for path in ('config/m10/services.json','schema/m10-services.schema.json','tools/m10/preflight.py',
                     'tests/m10/test_scope.py','qa/golden/m10/manifest.json','docs/porting/m10-report.md'):
            self.assertTrue(scope.is_public_m10_path(path))

    def test_no_private_generated_or_scope_escape(self):
        for path in ('config/m10/private.d88','tools/m10/output.bin','tools/m10/../../private.py',
                     'schema/m10/nested.schema.json','manifests/components.lock.json','components/fdkernel/source.c',
                     'docs/porting/m11-report.md','/config/m10/services.json'):
            self.assertFalse(scope.is_public_m10_path(path))


if __name__=='__main__':unittest.main()
