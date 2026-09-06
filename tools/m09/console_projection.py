#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""ROM-free console transition oracle; observations must come from a trace adapter.

Geometry and screen contents are local observation inputs, never public status.
This module does not establish firmware provenance or replace the L0-L9 gate.
"""


class ObservationError(ValueError):
    """Diagnostics deliberately exclude observed values."""


def transition(cells, cursor, character, *, blank_cell=32):
    """Model the declared logical-row BIOS policy, not renderer raster width."""
    if not cells or not cells[0] or any(len(row) != len(cells[0]) for row in cells):
        raise ObservationError("invalid logical display shape")
    rows, columns = len(cells), len(cells[0])
    if type(blank_cell) is not int or not 0 <= blank_cell <= 65535:
        raise ObservationError("invalid cleared-cell representation")
    x, y = cursor
    if not 0 <= x < columns or not 0 <= y < rows:
        raise ObservationError("cursor outside logical display")
    if character not in (10, 13) and not 32 <= character <= 126:
        raise ObservationError("unsupported character")
    result = [list(row) for row in cells]
    wrapped = scrolled = False
    if character == 13:
        x = 0
    elif character == 10:
        y += 1
    else:
        result[y][x] = character
        x += 1
        if x == columns:
            x = 0
            y += 1
            wrapped = True
    if y == rows:
        result = result[1:] + [[blank_cell] * columns]
        y -= 1
        scrolled = True
    return result, [x, y], wrapped, scrolled


def verify_sequence(initial_cells, initial_cursor, observations, message, *, blank_cell=32):
    """Check per-call guest effects, with ordering and real mutation witnesses.

    The adapter must obtain call/request/return sequence IDs at real guest
    instruction boundaries, and changed cells from actual writes. Merely
    copying expected state into observations is not a qualification mechanism.
    """
    if len(observations) != len(message):
        raise ObservationError("diagnostic call count mismatch")
    cells, cursor = initial_cells, initial_cursor
    previous = -1
    saw_wrap = saw_scroll = saw_printable = False
    for character, event in zip(message, observations):
        required = {"character", "call_sequence", "request_sequence", "return_sequence",
                    "cells", "cursor", "cell_write_sequences"}
        if set(event) != required:
            raise ObservationError("invalid observation fields")
        call, request, returned = (event[key] for key in
                                   ("call_sequence", "request_sequence", "return_sequence"))
        if any(type(value) is not int for value in (call, request, returned)):
            raise ObservationError("invalid instruction sequence type")
        if not previous < call < request < returned:
            raise ObservationError("guest request ordering mismatch")
        if event["character"] != character:
            raise ObservationError("guest diagnostic byte mismatch")
        writes = event["cell_write_sequences"]
        if not isinstance(writes, list) or any(type(seq) is not int or not request < seq < returned
                                              for seq in writes):
            raise ObservationError("display mutation outside guest request")
        if 32 <= character <= 126 and not writes:
            raise ObservationError("printable request has no actual display write")
        expected_cells, expected_cursor, wrapped, scrolled = transition(cells, cursor, character, blank_cell=blank_cell)
        if event["cells"] != expected_cells or event["cursor"] != expected_cursor:
            raise ObservationError("display transition mismatch")
        cells, cursor, previous = expected_cells, expected_cursor, returned
        saw_wrap |= wrapped
        saw_scroll |= scrolled
        saw_printable |= 32 <= character <= 126
    return {"exact_guest_message": True, "cursor_policy_verified": True,
            "printable_mutation_observed": saw_printable,
            "wrap_exercised": saw_wrap, "scroll_exercised": saw_scroll}
