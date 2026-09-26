#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Audit all M10 changed/untracked public text, staged blobs and new commits."""
import argparse
import importlib.util
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('prior_privacy', ROOT/'tools/m09/privacy_guard.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)


def audit(root, start, registered_tokens=()):
    def git(*args):return subprocess.check_output(['git','-C',str(root),*args])
    names=set(git('diff','--name-only',start).decode().splitlines())
    names.update(git('ls-files','--others','--exclude-standard').decode().splitlines())
    staged={line.split('\t',1)[1]:line.split()[0]
            for line in git('ls-files','--stage').decode().splitlines()}
    for name in sorted(names):
        if staged.get(name)=='160000':continue
        path=root/name
        if path.is_symlink():raise ValueError('symlink rejected')
        if path.is_file():prior.check_blob(name,path.read_bytes(),registered_tokens)
        if name in staged:prior.check_blob(name,git('show',':'+name),registered_tokens)
    for commit in git('rev-list',start+'..HEAD').decode().splitlines():
        for name in git('diff-tree','--no-commit-id','--name-only','-r',commit).decode().splitlines():
            entry=git('ls-tree',commit,'--',name).split()
            if not entry or entry[0]==b'160000':continue
            prior.check_blob(name,git('show',commit+':'+name),registered_tokens)
    return True


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--start',default='6b29d4f9b2b732ced9bc25a9b33b453877cbd7f0')
    args=parser.parse_args()
    try:audit(args.root,args.start)
    except (OSError,ValueError,subprocess.CalledProcessError):
        print('M10 public privacy audit failed; details withheld')
        return 1
    print('M10 public text, staged blobs and commit objects privacy audit passed')
    return 0


if __name__=='__main__':raise SystemExit(main())
