#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Check the clock fixture's persisted FAT timestamp independently of DOS."""
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/m05'), str(ROOT / 'tools/m14')]
from common import derive_layout, encode_dos_name
from inspect_media import parse_d88
from inspect_fat12 import inspect


def clock_timestamp(image, spec, results):
    _, files = inspect(image, spec)
    if files.get('CLOCK.DAT') != b'M15 clock and file timestamp\r\n':
        raise ValueError('CLOCK_PAYLOAD_MISMATCH')
    layout = derive_layout(spec)
    _, raw = parse_d88(image, spec, layout)
    fs, bps = spec['filesystem'], spec['geometry']['bytes_per_sector']
    start = (fs['reserved_sectors'] + fs['fat_count'] * fs['sectors_per_fat']) * bps
    directory = raw[start:start + layout['root_directory_sectors'] * bps]
    matches = [directory[n:n + 32] for n in range(0, len(directory), 32)
               if directory[n:n + 11] == encode_dos_name('CLOCK.DAT')]
    if len(matches) != 1:
        raise ValueError('CLOCK_DIRECTORY_ENTRY_MISSING_OR_AMBIGUOUS')
    packed_time, packed_date = struct.unpack_from('<HH', matches[0], 22)
    if packed_date != ((2024 - 1980) << 9) | (2 << 5) | 29:
        raise ValueError('CLOCK_PERSISTED_DATE')
    if packed_time >> 5 != ((12 << 6) | 34) or not 27 <= (packed_time & 31) <= 29:
        raise ValueError('CLOCK_PERSISTED_TIME')
    records = [r for r in results['records'] if r['case_id'] == 7039]
    if (len(records) != 1 or not records[0]['checked'] or records[0]['flags'] & 1 or
            (records[0]['cx'], records[0]['dx']) != (packed_time, packed_date)):
        raise ValueError('CLOCK_DOS_AND_DIRECTORY_TIMESTAMP_DISAGREE')
    return {'packed_time': packed_time, 'packed_date': packed_date,
            'dos_and_directory_agree': True}
