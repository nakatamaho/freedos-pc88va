#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Compare exactly one fresh CI build pair with the committed public golden."""
import json
from pathlib import Path
import sys
from record_public_builds import record

ROOT = Path(__file__).resolve().parents[2]
if len(sys.argv) == 2:
    selected = Path(sys.argv[1])
else:
    candidates = list((ROOT/'build').glob('m09-public.*'))
    if len(candidates) != 1:
        raise SystemExit('select an explicit public build pair; ambiguous generated roots')
    selected = candidates[0]
expected = json.loads((ROOT/'qa/golden/m09/manifest.json').read_text())
if record(selected) != expected:
    raise SystemExit('public clean-build manifest differs from golden')
print('Independent public build pair matches committed M09 golden')
