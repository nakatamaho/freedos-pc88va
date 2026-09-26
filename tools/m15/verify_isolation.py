#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Require an exported M15 build to contain no other milestone directories."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def verify(root):
    for category in ('tools', 'tests', 'config', 'containers'):
        for entry in (root / category).glob('m[0-9][0-9]'):
            if entry.name != 'm15':
                raise ValueError('Historical milestone directory in isolated build: ' + str(entry))
    for path in (root / 'tools/m15').rglob('*'):
        if path.suffix in ('.py', '.sh') or path.name == 'Dockerfile':
            if re.search(r'(?:tools|tests|config|containers)/m(?!15)[0-9]{2}(?:/|\b)', path.read_text()):
                raise ValueError('Cross-milestone runtime path in ' + str(path))


if __name__ == '__main__':
    verify(ROOT)
    print('M15 build export is isolated from other milestones')
