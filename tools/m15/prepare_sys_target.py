#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Prepare an empty SYS target; never copy executable system payloads to it."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/m15')]
from media import derive_layout, encode_dos_name
from media import build_boot_record, build_d88, set_fat12_entry
from media import inspect


def prepare(source, spec, token):
    if not token or len(token) > 30 or not token.isascii() or not token.isalnum():
        raise ValueError('TARGET_TOKEN_MUST_BE_1_TO_30_ASCII_ALNUM')
    summary, files = inspect(source, spec)
    loader = summary['files']['LOADER.BIN']
    chain = loader['clusters']
    if not chain or chain != list(range(chain[0], chain[0] + len(chain))):
        raise ValueError('SOURCE_LOADER_MUST_BE_CONTIGUOUS')
    layout = derive_layout(spec)
    fs, geo = spec['filesystem'], spec['geometry']
    bps = geo['bytes_per_sector']
    if bps != 1024 or fs['sectors_per_cluster'] != 1:
        raise ValueError('UNSUPPORTED_SYS_LAYOUT')
    raw = bytearray(geo['total_bytes'])
    raw[:bps] = build_boot_record(spec)  # Nonbooting self-loop, not source code.
    fat = bytearray(fs['sectors_per_fat'] * bps)
    set_fat12_entry(fat, 0, 0xf00 | fs['media_descriptor'])
    set_fat12_entry(fat, 1, 0xfff)
    root_start = (fs['reserved_sectors'] + fs['fat_count'] * fs['sectors_per_fat']) * bps
    free = iter(c for c in range(2, layout['data_clusters'] + 2) if c not in chain)
    payloads = {'LOADER.BIN': bytes(len(files['LOADER.BIN'])),
                'SYS.ID': token.encode('ascii') + b'\r\n',
                'SENTINEL.TXT': b'Original prepared-target sentinel.\r\n'}
    for index, (name, data) in enumerate(payloads.items()):
        allocated = chain if name == 'LOADER.BIN' else [
            next(free) for _ in range((len(data) + bps - 1) // bps)]
        for n, cluster in enumerate(allocated):
            set_fat12_entry(fat, cluster, allocated[n + 1] if n + 1 < len(allocated) else 0xfff)
            offset = (layout['first_data_sector'] + cluster - 2) * bps
            raw[offset:offset + bps] = data[n * bps:(n + 1) * bps].ljust(bps, b'\0')
        entry = bytearray(32)
        entry[:11] = encode_dos_name(name)
        entry[11] = 0x20
        struct.pack_into('<H', entry, 24, 33)  # 1980-01-01.
        struct.pack_into('<HI', entry, 26, allocated[0], len(data))
        raw[root_start + index * 32:root_start + (index + 1) * 32] = entry
    for n in range(fs['fat_count']):
        offset = (fs['reserved_sectors'] + n * fs['sectors_per_fat']) * bps
        raw[offset:offset + len(fat)] = fat
    result = build_d88(spec, bytes(raw))
    after, readback = inspect(result, spec)
    if readback != payloads or after['files']['LOADER.BIN']['clusters'] != chain:
        raise ValueError('PREPARED_TARGET_ROUNDTRIP')
    return result, {'scope': 'empty host preparation; guest transfer NOT RUN',
                    'source_sha256': hashlib.sha256(source).hexdigest(),
                    'prepared_sha256': hashlib.sha256(result).hexdigest(),
                    'source_boot_code_copied': False,
                    'system_payloads_copied': False, 'filesystem': after}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--target-token', required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    for path in (output, output.with_suffix('.json')):
        path.relative_to(ROOT)
        if path.exists() or path.is_symlink():
            raise ValueError('OUTPUT_EXISTS')
        if subprocess.run(['git', '-C', str(ROOT), 'check-ignore', '-q', '--', str(path)]).returncode:
            raise ValueError('OUTPUT_MUST_BE_GIT_EXCLUDED')
    result, record = prepare(args.source.read_bytes(),
                             json.loads((ROOT / 'config/m15/media.json').read_text()),
                             args.target_token)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.open('xb').write(result)
    output.with_suffix('.json').open('x').write(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    main()
