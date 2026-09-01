#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Parse D88 container structure without interpreting private disk content."""

from __future__ import annotations

import struct
from dataclasses import dataclass


HEADER_SIZE = 688
TRACK_SLOTS = 164
SECTOR_HEADER_SIZE = 16


class D88Error(ValueError):
    """A D88 structural invariant failed."""


@dataclass(frozen=True)
class Sector:
    """Structural metadata for one D88 sector record."""

    cylinder: int
    head: int
    record: int
    size_code: int
    sectors_in_track: int
    density: int
    deleted_data: int
    status: int
    seek_status: int
    rpm: int
    byte_length: int
    record_offset: int


@dataclass(frozen=True)
class Track:
    """A bounded D88 track region and its ordered sector metadata."""

    slot: int
    start: int
    end: int
    sectors: tuple[Sector, ...]


@dataclass(frozen=True)
class Image:
    """Validated public structural projection of a D88 image."""

    declared_size: int
    write_protected: bool
    media_type: int
    tracks: tuple[Track, ...]

    @property
    def sector_count(self) -> int:
        return sum(len(track.sectors) for track in self.tracks)


def _track_offsets(data: bytes, declared_size: int) -> list[tuple[int, int]]:
    offsets = list(struct.unpack_from("<164I", data, 32))
    first_empty = next((index for index, value in enumerate(offsets) if value == 0), len(offsets))
    if any(offsets[first_empty:]):
        raise D88Error("track offset appears after an empty track slot")
    populated = offsets[:first_empty]
    if not populated:
        raise D88Error("D88 contains no populated track")
    if populated != sorted(populated) or len(populated) != len(set(populated)):
        raise D88Error("track offsets descend, overlap, or duplicate")
    if populated[0] < HEADER_SIZE or any(offset >= declared_size for offset in populated):
        raise D88Error("track offset is outside the declared image")
    return list(enumerate(populated))


def parse(data: bytes) -> Image:
    """Validate a single D88 image and return metadata, never sector payloads."""

    if len(data) < HEADER_SIZE:
        raise D88Error("D88 header is truncated")
    declared_size = struct.unpack_from("<I", data, 28)[0]
    if declared_size != len(data):
        raise D88Error("declared D88 size or trailing-data boundary is invalid")
    indexed_offsets = _track_offsets(data, declared_size)
    seen_chr: set[tuple[int, int, int]] = set()
    tracks: list[Track] = []
    for position, (slot, start) in enumerate(indexed_offsets):
        end = indexed_offsets[position + 1][1] if position + 1 < len(indexed_offsets) else declared_size
        if end <= start:
            raise D88Error("track region is empty or overlapping")
        cursor = start
        expected_count: int | None = None
        sectors: list[Sector] = []
        while cursor < end:
            if cursor + SECTOR_HEADER_SIZE > end:
                raise D88Error("sector header is truncated")
            fields = struct.unpack_from("<BBBBHBBBB3sBH", data, cursor)
            cylinder, head, record, size_code, count, density, deleted, status, seek, reserved, rpm, length = fields
            if reserved != bytes(3):
                raise D88Error("sector reserved bytes are nonzero")
            if count == 0 or count > 64:
                raise D88Error("per-track sector count is invalid")
            if expected_count is None:
                expected_count = count
            elif expected_count != count:
                raise D88Error("per-track sector-count fields disagree")
            if size_code > 7 or length != 128 << size_code:
                raise D88Error("sector size code and payload length disagree")
            identity = (cylinder, head, record)
            if identity in seen_chr:
                raise D88Error("duplicate CHR sector record")
            seen_chr.add(identity)
            payload_end = cursor + SECTOR_HEADER_SIZE + length
            if payload_end > end:
                raise D88Error("sector payload is truncated or out of bounds")
            sectors.append(Sector(
                cylinder=cylinder,
                head=head,
                record=record,
                size_code=size_code,
                sectors_in_track=count,
                density=density,
                deleted_data=deleted,
                status=status,
                seek_status=seek,
                rpm=rpm,
                byte_length=length,
                record_offset=cursor,
            ))
            cursor = payload_end
            if len(sectors) > count:
                raise D88Error("track contains more sector records than declared")
        if expected_count is None or len(sectors) != expected_count:
            raise D88Error("track sector count does not match its records")
        if cursor != end:
            raise D88Error("track contains hidden or trailing bytes")
        tracks.append(Track(slot=slot, start=start, end=end, sectors=tuple(sectors)))
    return Image(
        declared_size=declared_size,
        write_protected=data[26] != 0,
        media_type=data[27],
        tracks=tuple(tracks),
    )
