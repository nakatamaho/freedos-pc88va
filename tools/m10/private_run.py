#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Explicit local-only entry point; no private inputs are inferred or printed."""
import os
from pathlib import Path
import subprocess
import sys
import re

if os.environ.get('CI'):
    raise SystemExit('Private execution is prohibited in public CI')
runner=os.environ.get('M10_PRIVATE_RUNNER')
expected=os.environ.get('M10_PRIVATE_RUNNER_SHA256')
if not runner or not expected:
    raise SystemExit('Local frozen runner and exact digest are required; private gate NOT RUN')
import hashlib
path=Path(runner).resolve()
if not re.fullmatch(r'[0-9a-f]{64}',expected) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
    raise SystemExit('Private runner identity rejected')
if path.parts[:2]==('/','tmp') or path.parts[:3]==('/','private','tmp'):
    raise SystemExit('Persistent ignored private storage is required')
if subprocess.run(['git','-C',str(path.parent),'check-ignore','--quiet',str(path)],capture_output=True).returncode:
    raise SystemExit('Private runner is not protected by Git exclusion')
# The frozen runner owns its explicit contracts, fresh output directories and
# launch/input/result/projection validation. No shell evaluation is permitted.
subprocess.run([sys.executable,'-B',str(path)],check=True)
