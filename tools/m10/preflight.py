#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Enforced M09 handoff gate; never requires lost historical private evidence."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('acceptance',ROOT/'tools/qa/milestone_acceptance.py')
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
START='6b29d4f9b2b732ced9bc25a9b33b453877cbd7f0'
VAEG='7463f9501d84701f50f3243d5067b6a9dfd0c2e7'
VAEG_JOBS=['uPD9002 architectural SST ratchet','production-memory CPU trace matrix',
           'ubuntu asan compatibility','standalone compatibility conformance','repo invariants',
           'PC-88VA guest-driver distribution','windows msys2 mingw64 compatibility',
           'ubuntu clang compatibility','macos fetch-sdl2 compatibility',
           'windows msys2 mingw64 release artifact','ubuntu gcc compatibility']


def verify(accepted):
    record=json.loads((ROOT/'config/m10/m09-handoff.json').read_text())
    gate.require(record['identities']['DOWNSTREAM_BASE_SHA']==START,'M10_START_DRIFT')
    gate.require(gate.git(accepted,'rev-parse',START+'^')==record['identities']['QUALIFIED_IMPLEMENTATION_SHA'],
                 'M09_DIRECT_PARENT_DRIFT')
    gate.verify_content(accepted,record)
    gate.verify_topology(accepted,record)
    gate.verify_live_ci(accepted,record)
    subprocess.run([sys.executable,'-B',str(accepted/'tools/m09/verify_m09.py')],cwd=accepted,check=True)
    endpoint='repos/nakatamaho/vaeg/actions/runs/33937050536'
    run=json.loads(subprocess.check_output(['gh','api',endpoint]))
    pages=json.loads(subprocess.check_output(['gh','api','--paginate','--slurp',endpoint+'/attempts/1/jobs?per_page=100']))
    claim={'repository':'nakatamaho/vaeg','run_id':33937050536,'attempt':1,'head_sha':VAEG,
           'workflow_path':'.github/workflows/build.yml','required_jobs':VAEG_JOBS,'manifest':{}}
    gate.verify_ci_claim(claim,run,[j for p in pages for j in p['jobs']])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--accepted-root',type=Path)
    args=parser.parse_args()
    try:
        record=json.loads((ROOT/'config/m10/m09-handoff.json').read_text())
        remote=gate.git(ROOT,'ls-remote','--heads','origin','refs/heads/'+record['branch']).split()
        gate.require(len(remote)==2 and remote[0]==START,'REMOTE_TIP_MISMATCH')
        subprocess.run(['git','-C',str(ROOT),'fetch','origin',record['branch']],check=True)
        accepted=args.accepted_root
        if accepted is None:
            accepted=ROOT/'build/m10-preflight/freedos-pc88va'
            if not accepted.exists():
                subprocess.run(['git','-C',str(ROOT),'worktree','add','--detach',str(accepted),START],check=True)
                subprocess.run(['git','-C',str(accepted),'submodule','update','--init','--recursive'],check=True)
        verify(accepted.resolve())
    except (OSError,ValueError,KeyError,TypeError,subprocess.CalledProcessError) as error:
        print(str(error) if isinstance(error,gate.Rejected) else 'M10_PREFLIGHT_ERROR')
        return 1
    print('M10 public prerequisite passed: fixed M09 handoff, actual instances and exact live CI identities')
    print('Private fresh prerequisite is a separate local gate; historical private reconstruction is not claimed')
    return 0


if __name__=='__main__':raise SystemExit(main())
