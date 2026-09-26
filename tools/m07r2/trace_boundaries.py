#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Classify abstract boot-trace boundaries without retaining private values."""

from __future__ import annotations

from dataclasses import dataclass


BOUNDARIES = (
    "firmware_fdd_request",
    "drive_ready_or_media_sense",
    "first_seek_or_track_selection",
    "first_read_request",
    "first_successful_sector_transfer",
    "transfer_destination_write",
    "first_instruction_fetch_from_transfer",
    "controlled_marker",
)


class BoundaryError(ValueError):
    """An abstract boundary sequence is invalid."""


@dataclass(frozen=True)
class Boundaries:
    """Monotonic abstract milestones from one private trace projection."""

    reached: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(set(self.reached)) != len(self.reached):
            raise BoundaryError("boundary sequence contains a duplicate")
        unknown = set(self.reached) - set(BOUNDARIES)
        if unknown:
            raise BoundaryError("boundary sequence contains an unknown name")
        positions = [BOUNDARIES.index(item) for item in self.reached]
        if positions != sorted(positions):
            raise BoundaryError("boundary sequence is not ordered")

    def has(self, name: str) -> bool:
        return name in self.reached


def classify(control: Boundaries, probe: Boundaries | None) -> str:
    """Return the M07R2 A-E class from redacted boundary presence."""

    if not control.has("firmware_fdd_request") and not control.has("first_instruction_fetch_from_transfer"):
        return "A"
    if probe is None or not probe.has("first_read_request"):
        return "B"
    if not probe.has("transfer_destination_write"):
        return "C"
    if not probe.has("controlled_marker"):
        return "D"
    return "E"


def divergence(control: Boundaries, probe: Boundaries) -> tuple[str | None, str | None]:
    """Return the last common and first differing abstract boundaries."""

    last_common = None
    for name in BOUNDARIES:
        control_has = control.has(name)
        probe_has = probe.has(name)
        if control_has == probe_has and control_has:
            last_common = name
            continue
        if control_has != probe_has:
            return last_common, name
    return last_common, None
