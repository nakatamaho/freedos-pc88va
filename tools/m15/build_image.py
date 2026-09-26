#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Build a complete M15 disk twice from committed source exports."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PARENT_INPUTS = ('tools/m15', 'tests/m15', 'config/m15',
                 'schema/m15-loader-overlay.schema.json',
                 'manifests/toolchains.lock.json', 'COPYING', 'LICENSE.md')


def call(*args):
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/m15-image')
    parser.add_argument('--image', default='freedos-pc88va-m01:local')
    args = parser.parse_args()
    if call('git', 'diff', 'HEAD', '--', '.', ':!components/fdkernel'):
        raise ValueError('Commit parent changes before exporting the build')
    sources = {'parent': call('git', 'rev-parse', 'HEAD')}
    for name in ('fdkernel', 'freecom', 'country'):
        path = 'components/' + name
        sources[name] = call('git', 'rev-parse', 'HEAD:' + path)
        if call('git', '-C', path, 'rev-parse', 'HEAD') != sources[name]:
            raise ValueError('Component checkout differs from parent gitlink: ' + name)
        if call('git', '-C', path, 'status', '--porcelain', '--untracked-files=no'):
            raise ValueError('Component tracked source is dirty: ' + name)
    output = args.output.resolve()
    output.relative_to(ROOT)
    if subprocess.run(['git', 'check-ignore', '-q', str(output / 'probe')], cwd=ROOT).returncode:
        raise ValueError('Build output must be Git-excluded')
    if output.exists():
        raise ValueError('Output already exists; choose a new M15_IMAGE_OUTPUT')
    info = json.loads(call('docker', 'image', 'inspect', args.image))[0]
    if (info['Os'], info['Architecture']) != ('linux', 'amd64'):
        raise ValueError('The pinned Linux/amd64 toolchain image is required')
    output.mkdir(parents=True)
    inputs = output / 'inputs'
    inputs.mkdir()
    archives = {}
    for name, sha in sources.items():
        repo = ROOT if name == 'parent' else ROOT / 'components' / name
        archive = inputs / (name + '.tar')
        with archive.open('xb') as f:
            command = ['git', '-C', str(repo), 'archive', sha]
            if name == 'parent':
                command.extend(PARENT_INPUTS)
            subprocess.run(command, stdout=f, check=True)
        archives[name] = hashlib.sha256(archive.read_bytes()).hexdigest()
    # This verifier dependency is separate from the guest toolchain. Fetch a
    # pinned Linux wheel once; both build containers remain network-disabled.
    subprocess.run([sys.executable, '-m', 'pip', 'download', '--disable-pip-version-check', '--no-cache-dir',
                    '--only-binary=:all:', '--no-deps', '--platform', 'manylinux2014_x86_64',
                    '--python-version', '310', '--implementation', 'cp', '--abi', 'cp310',
                    '--dest', str(inputs), 'unicorn==2.1.4'], check=True)
    wheel = next(inputs.glob('unicorn-*.whl'))
    results = []
    command = 'mkdir -p /work/entry && tar -xf /input/parent.tar -C /work/entry tools/m15/build_image.sh && bash /work/entry/tools/m15/build_image.sh'
    for number in (1, 2):
        cid = call('docker', 'create', '--platform', 'linux/amd64', '--network', 'none',
                   '-e', f'M15_BUILD_PASS={number}', '--entrypoint', 'bash', info['Id'], '-ec', command)
        try:
            subprocess.run(['docker', 'cp', str(inputs) + '/.', cid + ':/input'], check=True)
            with (output / f'build-{number}.log').open('xb') as f:
                subprocess.run(['docker', 'start', '-a', cid], stdout=f, stderr=subprocess.STDOUT, check=True)
            target = output / f'run-{number}'
            subprocess.run(['docker', 'cp', cid + ':/work/result', str(target)], check=True)
            results.append(json.loads((target / 'artifacts.json').read_text()))
        finally:
            subprocess.run(['docker', 'rm', '-f', cid], check=True, stdout=subprocess.DEVNULL)
    if results[0] != results[1]:
        raise ValueError('Independent clean builds differ')
    media = (output / 'run-1/media.d88').read_bytes()
    (output / 'media.d88').write_bytes(media)
    record = {'sources': sources, 'source_archives_sha256': archives, 'toolchain_image': info['Id'],
              'verifier_wheel_sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(),
              'two_clean_builds_equal': True, 'artifacts': results[0],
              'guest_boot': 'NOT RUN', 'hardware': 'NOT RUN'}
    (output / 'build.json').write_text(json.dumps(record, indent=2)+'\n')
    print('Two complete source builds match: ' + str(output / 'media.d88'))


if __name__ == '__main__':
    main()
