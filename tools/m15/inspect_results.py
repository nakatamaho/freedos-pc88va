#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Decode original guest observations without converting missing cases to PASS."""
import struct

FIELDS = ('case_id', 'input_ax', 'ax', 'bx', 'cx', 'dx', 'si', 'di', 'bp',
          'ds', 'es', 'flags', 'stack_delta', 'checked')

def decode(data):
    if len(data) < 12 or data[:4] != b'M15R':
        raise ValueError('RESULT_MAGIC_OR_LENGTH')
    version, size, count, failure = struct.unpack_from('<4H', data, 4)
    if version != 1 or size != 28 or count > 192 or len(data) != 12 + size * count:
        raise ValueError('RESULT_FORMAT_OR_COUNT')
    records = [dict(zip(FIELDS, struct.unpack_from('<14H', data, 12 + size * i)))
               for i in range(count)]
    if any(x['checked'] not in (0, 1) for x in records):
        raise ValueError('INVALID_CHECK_STATE')
    return {'first_failure': failure, 'records': records}

def require_complete(result, expected_ids):
    records = result['records']
    expected_ids = list(expected_ids)
    if (not expected_ids or len(set(expected_ids)) != len(expected_ids) or
            any(type(case) is not int or not 1 <= case <= 65535 for case in expected_ids)):
        raise ValueError('EMPTY_OR_INVALID_CASE_CONTRACT')
    if [x['case_id'] for x in records] != expected_ids:
        raise ValueError('MISSING_DUPLICATE_OR_REORDERED_CASE')
    if result['first_failure'] or any(not x['checked'] for x in records):
        raise ValueError('GUEST_ASSERTION_FAILED')
    if any(x['stack_delta'] for x in records):
        raise ValueError('INT21_STACK_NOT_BALANCED')
