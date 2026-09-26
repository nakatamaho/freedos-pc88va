# SPDX-License-Identifier: GPL-2.0-or-later
"""Missing or corrupt evidence must not be converted into guest acceptance."""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/m15'))
from inspect_results import decode, require_complete
from inspect_arena import decode as decode_arena


def records(ids=(1001, 1002), failed=0, stack=0):
    data = b'M15R' + struct.pack('<4H', 1, 28, len(ids), failed)
    for case in ids:
        data += struct.pack('<14H', case, 0x3D00, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0x202, stack, int(case != failed))
    return data


def chain(blocks):
    return (b'M15M' + struct.pack('<2H', 1, len(blocks)) +
            b''.join(struct.pack('<5H', *block) for block in blocks))


class ObservationRejectionTests(unittest.TestCase):
    def test_complete_ordered_record_is_accepted(self):
        require_complete(decode(records()), [1001, 1002])

    def test_missing_duplicate_extra_or_reordered_cases_are_rejected(self):
        for ids in ((1001,), (1001, 1001), (1002, 1001), (1001, 1002, 1003)):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                require_complete(decode(records(ids)), [1001, 1002])

    def test_actual_failure_or_unbalanced_stack_is_rejected(self):
        for data in (records(failed=1002), records(stack=2)):
            with self.assertRaises(ValueError):
                require_complete(decode(data), [1001, 1002])

    def test_empty_or_duplicate_case_contract_cannot_claim_acceptance(self):
        for ids in ((), (1001, 1001)):
            with self.assertRaises(ValueError):
                require_complete(decode(records(ids)), ids)

    def test_truncation_trailing_data_and_false_check_state_are_rejected(self):
        bad_check = bytearray(records())
        struct.pack_into('<H', bad_check, 12 + 26, 2)
        for data in (b'', records()[:-1], records() + b'\0', bytes(bad_check)):
            with self.assertRaises(ValueError):
                decode(data)

    def test_contiguous_chain_with_one_final_block_is_accepted(self):
        decoded = decode_arena(chain([(1, 0x1000, ord('M'), 0x1001, 15),
                                      (1, 0x1010, ord('Z'), 0, 31)]))
        self.assertEqual(len(decoded[0]['blocks']), 2)

    def test_partial_overlapping_gapped_cyclic_or_wrapped_arena_is_rejected(self):
        invalid = [
            [(1, 0x1000, ord('M'), 0, 15)],
            [(1, 0x1000, ord('M'), 0, 15), (1, 0x100F, ord('Z'), 0, 1)],
            [(1, 0x1000, ord('M'), 0, 15), (1, 0x1011, ord('Z'), 0, 1)],
            [(1, 0x1000, ord('M'), 0, 15), (1, 0x1000, ord('Z'), 0, 1)],
            [(1, 0xFFF0, ord('Z'), 0, 32)],
            [(1, 0x1000, ord('Z'), 0, 15), (1, 0x1010, ord('Z'), 0, 1)],
        ]
        for blocks in invalid:
            with self.subTest(blocks=blocks), self.assertRaises(ValueError):
                decode_arena(chain(blocks))


if __name__ == '__main__':
    unittest.main()
