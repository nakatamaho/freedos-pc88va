#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Run historical gates at immutable accepted checkouts, preserving their scope."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
scratch=ROOT/'build/m10-historical-scratch'
scratch.mkdir(parents=True,exist_ok=True)
os.environ['TMPDIR']=str(scratch)


def run(root,*command):subprocess.run(command,cwd=root,check=True)


def checkout(role,sha):
    root=Path(os.environ.get('M10_HISTORY_'+role.upper(),str(ROOT/'build'/('m10-history-'+role)/'freedos-pc88va')))
    if not root.exists():
        run(ROOT,'git','worktree','add','--detach',str(root),sha)
        run(root,'git','submodule','update','--init','--recursive')
    if subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()!=sha:
        raise ValueError('historical checkout identity drift')
    if subprocess.check_output(['git','-C',str(root),'status','--porcelain','--untracked-files=all'],text=True).strip():
        raise ValueError('historical checkout not clean')
    run(root,'bash','tools/configure_component_remotes.sh')
    return root


def baseline():
    root=checkout('baseline','f0edeaa35126cf6d027adac0316df5056f7b1ddb')
    run(root,'make','verify-scaffold','m04r1-license-verify','m04-verify','m01-host-portability','m01-image-identity')
    if not (root/'qa/results/m06/run-2').exists():
        run(root,'make','m01-preflight','m01-image','m01-build','m01-compare','m01-verify',
            'm02-preflight','m02-bundle','m02-compare','m02-verify',
            'm03-preflight','m03-scan','m03-compare','m03-verify',
            'm06-prepare-m05','m05-verify','m06')
    run(root,'make','m01-compare','m01-verify','m02-compare','m02-verify','m03-compare','m03-verify',
        'm05-compare','m05-negative-tests','m05-verify','m06-compare','m06-negative-tests','m06-verify',
        'm07-public','m07r2-public','m07r3-public','m07r4-public','m07r5-public','m07r6-public','m07-completion-public')


def loader_console():
    root=checkout('loader','cfdf5841857f9633a20bdb7b6edb0c1e35275969')
    run(root,'make','m08-public-verify')
    run(root,sys.executable,'-B','-m','unittest','tests/test_m08_media.py','tests/test_m08_acceptance.py')
    root=checkout('console','6b29d4f9b2b732ced9bc25a9b33b453877cbd7f0')
    run(root,'make','m09-public')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--loader-console-only',action='store_true');args=parser.parse_args()
    if not args.loader_console_only:baseline()
    loader_console()
    print('Historical regression gates passed at exact accepted checkouts; historical status records remain unchanged')
