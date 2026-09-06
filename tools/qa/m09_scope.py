# SPDX-License-Identifier: GPL-2.0-or-later
"""Exact public M09 scope shared by historical parent-boundary checks."""
from pathlib import PurePosixPath


def is_public_m09_path(value):
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts:
        return False
    exact = {
        'manifests/m09-components.lock.json',
        'docs/porting/m09-report.md',
        'docs/porting/m09-console-adr.md',
        '.github/workflows/m09-console.yml',
        'tools/qa/m09_scope.py',
    }
    if value in exact:
        return True
    groups = {
        'tools/m09/': {'.py', '.sh'},
        'tests/m09/': {'.py'},
        'config/m09/': {'.json'},
        'qa/golden/m09/': {'.json'},
    }
    if value.startswith('schema/m09-') and value.endswith('.schema.json') and len(path.parts) == 2:
        return True
    return any(value.startswith(prefix) and path.suffix in extensions
               for prefix, extensions in groups.items())
