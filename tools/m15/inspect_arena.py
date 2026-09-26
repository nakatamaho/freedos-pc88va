#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Validate complete guest MCB snapshots and the memory fixture's lifetime."""
import struct

SNAPSHOTS = (list(range(6006, 6014)) + [6016, 6017, 6019, 6020] +
             list(range(6026, 6058)) + [6059])
MEMORY_CASES = (list(range(6001, 6006)) + [6061] + list(range(6006, 6016)) +
                [6062] + list(range(6016, 6021)) + list(range(6022, 6061)))


def decode(data):
    if len(data) < 8 or data[:4] != b'M15M':
        raise ValueError('MCB_MAGIC_OR_LENGTH')
    version, count = struct.unpack_from('<2H', data, 4)
    if version != 1 or not 1 <= count <= 2048 or len(data) != 8 + count * 10:
        raise ValueError('MCB_FORMAT_OR_COUNT')
    snapshots = []
    seen = set()
    for offset in range(8, len(data), 10):
        case, segment, kind, owner, paragraphs = struct.unpack_from('<5H', data, offset)
        if not case or kind not in (ord('M'), ord('Z')):
            raise ValueError('MCB_CASE_OR_TYPE')
        if not snapshots or snapshots[-1]['case_id'] != case:
            if case in seen:
                raise ValueError('MCB_REPEATED_SNAPSHOT')
            seen.add(case)
            snapshots.append({'case_id': case, 'blocks': []})
        snapshots[-1]['blocks'].append({'segment': segment, 'type': chr(kind),
                                       'owner': owner, 'paragraphs': paragraphs})
    for snapshot in snapshots:
        blocks = snapshot['blocks']
        if len(blocks) > 256 or blocks[-1]['type'] != 'Z':
            raise ValueError('MCB_CHAIN_TRUNCATED_OR_TOO_LONG')
        for index, block in enumerate(blocks):
            end = block['segment'] + 1 + block['paragraphs']
            if not block['segment'] or end > 0xFFFF:
                raise ValueError('MCB_CHAIN_WRAP')
            if index + 1 < len(blocks):
                if block['type'] != 'M' or end != blocks[index + 1]['segment']:
                    raise ValueError('MCB_CHAIN_OVERLAP_GAP_OR_EARLY_END')
    return snapshots


def require_memory_lifetime(snapshots, result):
    if [snapshot['case_id'] for snapshot in snapshots] != SNAPSHOTS:
        raise ValueError('MCB_MISSING_OR_UNEXPECTED_SNAPSHOT')
    if ([record['case_id'] for record in result['records']] != MEMORY_CASES or
            result['first_failure']):
        raise ValueError('MCB_CASE_RECORDS_INCOMPLETE')
    records = {record['case_id']: record for record in result['records']}
    if any(not record['checked'] or record['stack_delta'] for record in records.values()):
        raise ValueError('MCB_GUEST_ASSERTION_OR_STACK')
    psp = records[6002]['bx']
    initial = snapshots[0]['blocks']
    initial_owned = sum(block['owner'] == psp for block in initial)
    first = initial[0]['segment']
    final = initial[-1]['segment'] + initial[-1]['paragraphs'] + 1
    if snapshots[-1]['blocks'] != initial:
        raise ValueError('MCB_FINAL_OWNERSHIP_OR_EXTENTS_DIFFER')
    for snapshot in snapshots:
        case, blocks = snapshot['case_id'], snapshot['blocks']
        if (blocks[0]['segment'] != first or
                blocks[-1]['segment'] + blocks[-1]['paragraphs'] + 1 != final):
            raise ValueError('MCB_ARENA_BOUNDARY_DRIFT')
        extra = 2 if case in (6008, 6009) else int(
            case in (6007, 6010, 6011, 6012, 6016, 6019) or
            6026 <= case <= 6057 and case % 2 == 0)
        if sum(block['owner'] == psp for block in blocks) != initial_owned + extra:
            raise ValueError('MCB_OWNED_BLOCK_LEAK_OR_LOSS')
    resized = next(snapshot for snapshot in snapshots if snapshot['case_id'] == 6011)
    address = records[6007]['ax'] - 1
    block = next((block for block in resized['blocks'] if block['segment'] == address), None)
    if block is None or block['owner'] != psp or block['paragraphs'] != records[6011]['bx']:
        raise ValueError('MCB_RESIZE_FAILURE_STATE_MISMATCH')
    if not records[6011]['flags'] & 1 or records[6011]['ax'] != 8:
        raise ValueError('MCB_RESIZE_FAILURE_STATUS')
    if records[6006]['bx'] != records[6014]['bx'] or records[6006]['bx'] != records[6059]['bx']:
        raise ValueError('MCB_LARGEST_BLOCK_NOT_RECOVERED')
    return {'snapshots': len(snapshots), 'repeated_allocation_cycles': 16,
            'complete_chain_restored': True, 'arena_first': first,
            'arena_end': final, 'caller_owned_blocks': initial_owned}
