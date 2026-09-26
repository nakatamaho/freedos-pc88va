#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Archive the reproducible M15 distribution and its public provenance."""
import argparse
import hashlib
import json
import lzma
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def identity(data):
    return {'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    args = parser.parse_args()
    record = json.loads((args.build / 'build.json').read_text())
    data = (args.build / 'media.d88').read_bytes()
    if record['two_clean_builds_equal'] is not True:
        raise ValueError('Two independent builds must have matched')
    if identity(data) != record['artifacts']['media.d88']:
        raise ValueError('Distribution differs from the recorded build')
    for number in (1, 2):
        if (args.build / f'run-{number}/media.d88').read_bytes() != data:
            raise ValueError('Distribution differs from an independent build')
    compressed = lzma.compress(data, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64, preset=9)
    if lzma.decompress(compressed) != data:
        raise ValueError('XZ roundtrip failed')
    output = ROOT / 'images/milestones/m15'
    output.mkdir(parents=True, exist_ok=True)
    for name in ('media.d88.xz', 'manifest.json'):
        if (output / name).exists():
            raise ValueError('Distribution already exists; review replacement explicitly')
    manifest = {'milestone': 'M15', 'sources': record['sources'],
                'toolchain_image': record['toolchain_image'],
                'source_archives_sha256': record['source_archives_sha256'],
                'two_clean_builds_equal': True,
                'media.d88': identity(data), 'media.d88.xz': identity(compressed)}
    (output / 'media.d88.xz').write_bytes(compressed)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('Archived M15 distribution:', output)


if __name__ == '__main__':
    main()
