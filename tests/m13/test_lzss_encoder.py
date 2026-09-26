#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""ROM-free independent checks for the unchanged 8086 LZSS token format."""
from functools import lru_cache
import importlib.util
import itertools
from pathlib import Path
import random
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("lzss_carrier", ROOT / "tools/m13/build_compressed_kernel.py")
CARRIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CARRIER)


def decode(encoded, size):
    output, cursor, matches = bytearray(), 0, []
    while len(output) < size:
        flags = encoded[cursor]
        cursor += 1
        for bit in range(8):
            if len(output) == size:
                if flags >> bit:
                    raise AssertionError("nonzero unused token flags")
                break
            if flags & (1 << bit):
                low, high = encoded[cursor:cursor + 2]
                cursor += 2
                distance = (((high >> 4) << 8) | low) + 1
                count = (high & 15) + 3
                if not 1 <= distance <= min(4096, len(output)) or len(output) + count > size:
                    raise AssertionError("match exceeds initialized history or output")
                matches.append((len(output), distance, count))
                for _ in range(count):
                    output.append(output[-distance])
            else:
                output.append(encoded[cursor])
                cursor += 1
    if cursor != len(encoded):
        raise AssertionError("trailing encoded bytes")
    return bytes(output), matches


def exhaustive_cost(body):
    @lru_cache(None)
    def visit(position, slot):
        if position == len(body):
            return 0
        flag = int(slot == 0)
        next_slot = (slot + 1) % 8
        cost = flag + 1 + visit(position + 1, next_slot)
        for distance in range(1, min(position, 4096) + 1):
            for length in range(1, min(18, len(body) - position) + 1):
                if body[position + length - 1] != body[position + length - 1 - distance]:
                    break
                if length >= 3:
                    cost = min(cost, flag + 2 + visit(position + length, next_slot))
        return cost
    return visit(0, 0)


class LzssEncoderTests(unittest.TestCase):
    def test_short_binary_inputs_have_minimum_encoded_byte_cost(self):
        for size in range(13):
            for symbols in itertools.product(b"AB", repeat=size):
                body = bytes(symbols)
                encoded = CARRIER.compress(body)
                self.assertEqual(decode(encoded, size)[0], body)
                self.assertEqual(len(encoded), exhaustive_cost(body), repr(body))

    def test_roundtrip_empty_literals_overlaps_and_window_edges(self):
        rng = random.Random(0x1400)
        noise = bytes(rng.randrange(256) for _ in range(4096))
        cases = [b"", bytes(range(1, 30)), b"A" * 1000, b"AB" * 1000,
                 noise + noise[:18], noise + b"!" + noise[:18],
                 bytes(range(256)) * 33]
        for body in cases:
            with self.subTest(size=len(body)):
                first = CARRIER.compress(body)
                self.assertEqual(first, CARRIER.compress(body))
                self.assertEqual(decode(first, len(body))[0], body)
        _, matches = decode(CARRIER.compress(noise + noise[:18]), 4114)
        self.assertIn((4096, 4096, 18), matches)


if __name__ == "__main__":
    unittest.main()
