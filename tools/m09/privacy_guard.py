#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Audit new public worktree and staged blobs, without reading private inputs."""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
START = 'cfdf5841857f9633a20bdb7b6edb0c1e35275969'
FORBIDDEN_SUFFIXES = {'.bin', '.rom', '.img', '.d88', '.exe', '.o', '.obj',
                      '.tar', '.zip', '.log', '.trace', '.dat', '.sys', '.com'}


def check_blob(name, data, registered_tokens=()):
    if Path(name).suffix.lower() in FORBIDDEN_SUFFIXES:
        raise ValueError('generated or private artifact rejected')
    if any(part in {'private-results', '.private-evidence'} for part in Path(name).parts):
        raise ValueError('private evidence rejected')
    if b'\0' in data or data.startswith((b'\x7fELF', b'MZ')):
        raise ValueError('binary public input rejected')
    # Split the pattern literals to avoid a self-match when auditing this file.
    if re.search(rb'/' + rb'(?:Users|home|private/tmp)/', data):
        raise ValueError('absolute local path rejected')
    if any(token and token in data for token in registered_tokens):
        raise ValueError('registered private identity rejected')


def audit(root=ROOT):
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=root)
    names = set(git('diff', '--name-only', START).decode().splitlines())
    names.update(git('diff', '--cached', '--name-only').decode().splitlines())
    names.update(name for name in git('ls-files', '--others', '--exclude-standard').decode().splitlines()
                 if any(part in name for part in ('/m09/', '/m09-', 'm09_scope.py')))
    staged = {line.split('\t', 1)[1]: line.split()[0]
              for line in git('ls-files', '--stage').decode().splitlines()}
    for name in sorted(names):
        if staged.get(name) == '160000':
            continue
        path = root/name
        if path.is_symlink():
            raise ValueError('symlink public input rejected')
        if path.is_file():
            check_blob(name, path.read_bytes())
        if name in staged:
            check_blob(name, git('show', ':'+name))
    return True


if __name__ == '__main__':
    try:
        audit()
    except (OSError, ValueError, subprocess.CalledProcessError):
        raise SystemExit('M09 public/private audit failed; details withheld') from None
    print('M09 public worktree and staged text audit passed')
