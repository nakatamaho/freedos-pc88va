# SPDX-License-Identifier: GPL-2.0-or-later
"""Exact M10 public parent paths, shared by historical scope checks."""
from pathlib import PurePosixPath


def is_public_m10_path(value):
    path=PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts:return False
    exact={'manifests/m10-components.lock.json','docs/porting/m10-report.md',
           'docs/porting/m10-machine-services-adr.md','.github/workflows/m10-machine-services.yml',
           '.github/workflows/m09-console.yml','tools/qa/milestone_acceptance.py',
           'tools/qa/m10_scope.py','tests/qa/test_milestone_acceptance.py'}
    if value in exact:return True
    if value.startswith('schema/m10-') and value.endswith('.schema.json') and len(path.parts)==2:return True
    groups={'tools/m10/':{'.py','.sh'},'tests/m10/':{'.py'},'config/m10/':{'.json'},'qa/golden/m10/':{'.json'}}
    return any(value.startswith(prefix) and path.suffix in suffixes for prefix,suffixes in groups.items())
