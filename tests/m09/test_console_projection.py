# SPDX-License-Identifier: GPL-2.0-or-later
"""Project-authored synthetic observations, not private firmware fixtures."""
import copy
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location(
    "console_projection", Path(__file__).resolve().parents[2] / "tools/m09/console_projection.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ProjectionTests(unittest.TestCase):
    def fixture(self):
        # Explicit snapshots provide an independent oracle for the transition model.
        start = [[32, 32], [32, 32]]
        message = b"ABC\r\nD"
        states = [([[65, 32], [32, 32]], [1, 0]),
                  ([[65, 66], [32, 32]], [0, 1]),
                  ([[65, 66], [67, 32]], [1, 1]),
                  ([[65, 66], [67, 32]], [0, 1]),
                  ([[67, 32], [32, 32]], [0, 1]),
                  ([[67, 32], [68, 32]], [1, 1])]
        observations = []
        for index, (character, (cells, cursor)) in enumerate(zip(message, states)):
            seq = index * 10
            observations.append(dict(character=character, call_sequence=seq,
                                     request_sequence=seq + 1, return_sequence=seq + 9,
                                     cells=cells, cursor=cursor,
                                     cell_write_sequences=[seq + 3] if character >= 32 else []))
        return start, [0, 0], observations, message

    def test_wrap_scroll_and_crlf(self):
        result = MODULE.verify_sequence(*self.fixture())
        self.assertTrue(all(result.values()))

    def test_host_only_marker_rejected(self):
        fixture = self.fixture()
        fixture[2][0]["cell_write_sequences"] = []
        with self.assertRaisesRegex(MODULE.ObservationError, "no actual display write"):
            MODULE.verify_sequence(*fixture)

    def test_wrong_cell_rejected(self):
        fixture = self.fixture()
        fixture[2][0]["cells"][0][0] = 90
        with self.assertRaisesRegex(MODULE.ObservationError, "transition mismatch"):
            MODULE.verify_sequence(*fixture)

    def test_out_of_order_request_rejected(self):
        fixture = self.fixture()
        fixture[2][1]["call_sequence"] = 0
        with self.assertRaisesRegex(MODULE.ObservationError, "ordering mismatch"):
            MODULE.verify_sequence(*fixture)

    def test_unrelated_write_rejected(self):
        fixture = self.fixture()
        fixture[2][0]["cell_write_sequences"] = [99]
        with self.assertRaisesRegex(MODULE.ObservationError, "outside guest request"):
            MODULE.verify_sequence(*fixture)

    def test_private_extra_field_rejected_without_echo(self):
        fixture = self.fixture()
        fixture[2][0]["private_input"] = "synthetic-secret"
        with self.assertRaises(MODULE.ObservationError) as raised:
            MODULE.verify_sequence(*fixture)
        self.assertNotIn("synthetic-secret", str(raised.exception))

    def test_repeated_projection_equal(self):
        fixture = self.fixture()
        self.assertEqual(MODULE.verify_sequence(*fixture),
                         MODULE.verify_sequence(*copy.deepcopy(fixture)))

    def test_lf_preserves_column(self):
        cells, cursor, wrap, scroll = MODULE.transition([[32] * 4 for _ in range(3)], [2, 0], 10)
        self.assertEqual(cursor, [2, 1])
        self.assertFalse(wrap or scroll)

    def test_overlay_selects_clear_representation(self):
        cells, cursor, wrap, scroll = MODULE.transition([[65, 66], [67, 68]], [1, 1], 10, blank_cell=0)
        self.assertEqual(cells, [[67, 68], [0, 0]])
        self.assertEqual(cursor, [1, 1])
        self.assertTrue(scroll)

    def test_invalid_clear_representation_rejected(self):
        with self.assertRaises(MODULE.ObservationError):
            MODULE.transition([[32]], [0, 0], 10, blank_cell=-1)


if __name__ == "__main__":
    unittest.main()
