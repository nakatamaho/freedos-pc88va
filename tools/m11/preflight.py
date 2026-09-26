#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Verify the immutable M10 handoff before M11 work is accepted."""
import subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
START='1acd1fbc0d556ec511ba71be833a1c7144eec841'
def main():
    branch='topic/m10-pc88va-machine-services-init'
    remote=subprocess.check_output(['git','-C',str(ROOT),'ls-remote','origin','refs/heads/'+branch],text=True).split()
    if len(remote)!=2 or remote[0]!=START: raise SystemExit('M11_PREFLIGHT_REMOTE_TIP_MISMATCH')
    subprocess.run([sys.executable,'-B','tools/m10/preflight.py'],cwd=ROOT,check=True)
    print('M11 M10 publication prerequisite passed')
if __name__=='__main__': main()
