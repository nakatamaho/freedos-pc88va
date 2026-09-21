#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Build the bounded M13 compressed-kernel carrier.

The common DOS kernel is a normal relocatable MZ image.  M08 accepts only a
zero-relocation image whose file and transformed allocation fit one 16-bit
segment, so this tool creates a small zero-relocation carrier.  Its resident
bridge expands the original body into the M13-owned extended image interval,
then applies the original relocation words and transfers to the original
entry.  The carrier is deterministic and contains no private machine values.
"""

from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
import re
from pathlib import Path
import struct
import subprocess
import tempfile


MAX_CARRIER_FILE = 65520
WINDOW = 4096
MAX_MATCH = 18
MIN_MATCH = 3
RING_BYTES = 4096
RELOCATION_OFFSET = 4096
BRIDGE_STACK_BOTTOM = 0xF000


def split_image(body, relocations, link_map, image_segment, memory_top=0xA0000,
                init_top=None, runtime_top=False):
    """Translate enumerated MZ targets; never search the image for opcodes.

    The only special HMA references are real relocated CALL/JMP operands and
    the two segment-valued bounds in Dyn/MoveKernel. Unknown uses fail closed.
    Shared NEAR data stays in DGROUP. INIT's entire FAR code group moves.
    """
    sections = {}
    for line in link_map.read_text().split('Memory Map', 1)[0].splitlines():
        m = re.match(r'^(\S+)\s+(\S+)\s+(\S+)\s+([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\s+([0-9a-fA-F]{8})$', line)
        if m:
            name, cls, group, seg, off, size = m.groups()
            sections[name] = (cls, group, int(seg, 16), int(off, 16), int(size, 16))
    init = sections['M13_INIT_TEXT']
    hma = sections['HMA_TEXT']
    if init[:2] != ('M13INIT', 'M13_INIT_GROUP') or init[3] != 0 or hma[3] != 0:
        raise ValueError('unsupported INIT/HMA group layout')
    init_at, init_size = init[2] * 16, init[4]
    hma_at, hma_size = hma[2] * 16, (hma[4] + 15) & ~15
    low_end = max(seg * 16 + off + size for name, (cls, group, seg, off, size)
                  in sections.items() if size and cls not in ('M13INIT', 'STACK'))
    resident = image_segment * 16 + ((low_end + 15) & ~15)
    if init_top is None:
        init_top = memory_top
    if not 0 < init_top <= memory_top:
        raise ValueError('INIT placement top is outside the selected memory')
    init_dest = (init_top - 4096 - ((init_size + 15) & ~15)) & ~15
    init_stack = init_dest + ((init_size + 15) & ~15)
    old_stack = sections['_STACK'][2] * 16 + sections['_STACK'][3]
    if not (0 < hma_size <= init_size <= 65535 and
            low_end <= init_at and init_at + init_size <= old_stack and
            resident + hma_size < init_dest and init_at + init_size <= len(body)):
        raise ValueError('split sections do not have disjoint valid lifetimes')
    updated = bytearray(body)
    changes = []
    for off, seg in struct.iter_unpack('<HH', relocations):
        at = seg * 16 + off
        target = struct.unpack_from('<H', body, at)[0]
        new, domain = target, 'resident'
        if target == init[2]:
            new, domain = init_dest // 16 - image_segment, 'init'
        elif target == hma[2]:
            if at >= 3 and body[at - 3] in (0x9A, 0xEA):
                target_offset = struct.unpack_from('<H', body, at - 2)[0]
                if target_offset < hma_size:
                    new, domain = resident // 16 - image_segment, 'assembly-copy'
                else:
                    domain = 'resident-bootstrap'
            elif (at >= 1 and body[at-1] == 0xB8) or (at >= 4 and body[at-4:at-2] == b'\xc7\x06'):
                domain = 'original-assembly-bound'
            else:
                raise ValueError('unclassified relocated HMA segment reference')
        if not 0 <= new <= 0xFFFF - image_segment:
            raise ValueError('translated segment is not representable')
        struct.pack_into('<H', updated, at, new)
        changes.append({'at': at, 'old': target, 'translated': new, 'domain': domain})
    marker = b'M13PLAN1'
    if updated.count(marker) != 1:
        raise ValueError('missing or ambiguous placement descriptor')
    at = updated.index(marker)
    if at + 24 > low_end or updated[at+8:at+24] != bytes(16):
        raise ValueError('descriptor is not an unfilled resident record')
    # The low-staging profile keeps the carrier below the high temporary INIT
    # envelope.  Its ceiling is therefore supplied by the native adapter at
    # boot; a carrier built with one capacity must remain valid at every
    # supported VA capacity.  Capacity-specific (non-low-staging) images
    # retain their explicit build-time ceiling.
    descriptor_top = 0 if runtime_top else memory_top // 16
    struct.pack_into('<8H', updated, at+8, image_segment, resident // 16,
                     init_dest // 16, init_size, init_stack // 16, 4096,
                     descriptor_top, 1)
    return bytes(updated), {
        'resident_text': [resident, resident + hma_size],
        'init_source': [image_segment * 16 + init_at, image_segment * 16 + init_at + init_size],
        'init': [init_dest, init_dest + init_size], 'init_stack': [init_stack, init_top],
        'hma_source': [image_segment * 16 + hma_at, image_segment * 16 + hma_at + hma_size],
        'descriptor': image_segment * 16 + at, 'fixups': changes,
    }


def plan_layout(header, body, relocations, *, image_segment, load_segment,
                file_segment, scratch_segment, source_extent,
                bridge_in_allocation=False,
                protected_end=0x10000, memory_top=0xA0000):
    """Check physical ownership while the copied bridge is still running.

    Carrier input is dead once copied into scratch; bridge and scratch are
    not. BSS/minimum allocation and the exact linked stack are included.
    """
    for value in (image_segment, load_segment, file_segment, scratch_segment):
        if not 0 <= value <= 0xFFFF:
            raise ValueError('segment outside 16-bit representation')
    image = image_segment * 16
    stack = header[7] * 16
    if header[8] != 4096 or stack < len(body):
        raise ValueError('linked stack must own a separate 4096-byte range')
    extent = max(((len(body) + 15) // 16 + header[5]) * 16,
                 stack + header[8])
    zero_bytes = extent - len(body)
    if zero_bytes + (len(body) & 15) > 65535:
        raise ValueError('zero-fill extent exceeds the bounded string operation')
    entry = header[11] * 16 + header[10]
    if entry >= len(body):
        raise ValueError('entry is outside linked image bytes')
    in_place = load_segment == file_segment
    bridge_start = load_segment * 16 if bridge_in_allocation else file_segment * 16
    bridge_end = (bridge_start + MAX_CARRIER_FILE if bridge_in_allocation
                  else bridge_start + 0x1000)
    ranges = {
        'image': (image, image + extent),
        'bridge': (bridge_start, bridge_end),
        # In-place mode uses the former metadata workspace as a bounded
        # bridge stack.  The compressed source and history ring stay in the
        # single low staging segment.
        'scratch': (scratch_segment * 16,
                    scratch_segment * 16 + (0x1000 if in_place else source_extent)),
    }
    for name, (start, end) in ranges.items():
        if not protected_end <= start < end <= memory_top:
            raise ValueError(name + ' exceeds owned conventional memory')
    for i, (name, (start, end)) in enumerate(ranges.items()):
        for other, (lo, hi) in list(ranges.items())[i + 1:]:
            if start < hi and lo < end:
                raise ValueError(name + ' overlaps live ' + other)
    carrier = (file_segment * 16 if in_place else load_segment * 16,
               (file_segment * 16 if in_place else load_segment * 16) + MAX_CARRIER_FILE)
    if not protected_end <= carrier[0] < carrier[1] <= memory_top:
        raise ValueError('carrier exceeds owned conventional memory')
    for name in ('bridge', 'scratch'):
        lo, hi = ranges[name]
        if not ((in_place or bridge_in_allocation) and name == 'bridge') and carrier[0] < hi and lo < carrier[1]:
            raise ValueError('carrier overlaps ' + name + ' during source copy')
    for offset, segment in struct.iter_unpack('<HH', relocations):
        at = segment * 16 + offset
        if offset == 0xFFFF or at + 2 > len(body):
            raise ValueError('relocation word outside linked bytes')
        target = struct.unpack_from('<H', body, at)[0]
        if image_segment + target > 0xFFFF:
            raise ValueError('relocation segment addition wraps')
    return {'ranges': ranges, 'image_extent': extent, 'in_place': in_place,
            'stack': (image + stack, image + stack + header[8]),
            'entry': image + entry, 'zero_bytes': zero_bytes}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_mz(data: bytes) -> tuple[tuple[int, ...], bytes, bytes]:
    if len(data) < 32 or data[:2] != b"MZ":
        raise ValueError("input is not a DOS MZ image")
    header = struct.unpack_from("<14H", data)
    cblp, cp, reloc_count, paragraphs = header[1], header[2], header[3], header[4]
    if not cp or cp > 511 or cblp > 511:
        raise ValueError("input MZ page encoding is outside the bounded contract")
    encoded = cp * 512 if cblp == 0 else (cp - 1) * 512 + cblp
    if encoded != len(data):
        raise ValueError("input MZ page encoding does not match file size")
    header_bytes = paragraphs * 16
    if header_bytes < 32 or header_bytes >= len(data):
        raise ValueError("input MZ header extent is invalid")
    reloc_offset = header[12]
    reloc_end = reloc_offset + reloc_count * 4
    if reloc_offset < 28 or reloc_end > header_bytes:
        raise ValueError("input MZ relocation table is outside its header")
    body = data[header_bytes:]
    relocations = data[reloc_offset:reloc_end]
    if not body:
        raise ValueError("input MZ body is empty")
    return header, body, relocations


def compress(body: bytes) -> bytes:
    """Minimize encoded bytes in the existing 8086 literal/match format.

    Include the flag byte for each group of eight tokens in the suffix cost.
    A longest match also represents every shorter legal match at that position;
    token distance has fixed cost. Ties prefer the longer token and the nearest
    source for its longest match. No decoder or history-window change is needed.
    """
    history = {}
    matches = []
    for position in range(len(body)):
        expired = position - WINDOW - 1
        if expired >= 0:
            old_key = body[expired:expired + MIN_MATCH]
            history[old_key].popleft()
            if not history[old_key]:
                del history[old_key]
        key = body[position:position + MIN_MATCH]
        candidates = history.setdefault(key, deque())
        best_length, best_distance = 0, 0
        for candidate in reversed(candidates):
            if len(key) != MIN_MATCH:
                break
            distance, length = position - candidate, MIN_MATCH
            while length < MAX_MATCH and position + length < len(body):
                source = position + length - distance
                if body[source] != body[position + length]:
                    break
                length += 1
            if length > best_length:
                best_length = length
                best_distance = distance
            if length == MAX_MATCH:
                break
        matches.append((best_length, best_distance))
        candidates.append(position)

    costs = [[0] * 8 for _ in range(len(body) + 1)]
    for position in range(len(body) - 1, -1, -1):
        maximum, _ = matches[position]
        for slot in range(8):
            next_slot = (slot + 1) & 7
            best = 1 + costs[position + 1][next_slot]
            for length in range(MIN_MATCH, maximum + 1):
                best = min(best, 2 + costs[position + length][next_slot])
            costs[position][slot] = int(slot == 0) + best

    encoded = bytearray()
    position = 0
    while position < len(body):
        flag_offset = len(encoded)
        encoded.append(0)
        flags = 0
        for bit in range(8):
            if position >= len(body):
                break
            maximum, best_distance = matches[position]
            next_slot = (bit + 1) & 7
            best_length = 1
            best_cost = 1 + costs[position + 1][next_slot]
            for length in range(MIN_MATCH, maximum + 1):
                cost = 2 + costs[position + length][next_slot]
                if cost <= best_cost:
                    best_length, best_cost = length, cost
            if best_length >= MIN_MATCH:
                distance = best_distance - 1
                encoded.append(distance & 0xFF)
                encoded.append(((distance >> 8) & 0x0F) << 4 | (best_length - MIN_MATCH))
                flags |= 1 << bit
                position += best_length
            else:
                encoded.append(body[position])
                position += 1
        encoded[flag_offset] = flags
    return bytes(encoded)


def assemble_bridge(source: Path, definitions: dict[str, int], output: Path) -> bytes:
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="m13-bridge-", dir=output.parent) as temporary:
        include = Path(temporary) / "definitions.inc"
        include.write_text("".join(f"%define {name} {value}\n" for name, value in sorted(definitions.items())))
        result = subprocess.run(
            ["nasm", "-f", "bin", "-DPC88VA", "-p", str(include), "-o", str(output), str(source)],
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise ValueError("M13 bridge assembly failed")
    return output.read_bytes()


def build(kernel: Path, bridge: Path, output: Path, *, load_segment: int,
          file_segment: int, scratch_segment: int, source_offset: int,
          image_segment: int = 0x1000, link_map: Path | None = None,
          memory_top: int = 0xA0000, split_init: bool = True,
          bridge_in_allocation: bool = False) -> dict:
    header, original_body, relocations = parse_mz(kernel.read_bytes())
    linked_body = original_body
    split = None
    in_place = load_segment == file_segment
    if b'M13PLAN1' in original_body and split_init:
        if link_map is None:
            raise ValueError('split image requires its matched link map')
        # A 256 KiB machine cannot place INIT at the conventional top while
        # the fixed low-staging carrier occupies 27000h..36ff0h.  Put the
        # short-lived INIT image immediately below staging; its stack is then
        # dead before the bridge takes ownership of the staging segment.
        # The in-place carrier is deliberately below the resident image's
        # high INIT envelope.  Once the bridge transfers to the expanded
        # kernel, the carrier is dead and the whole interval is available to
        # the temporary DOS arena.  Keeping INIT at the native top leaves
        # enough contiguous space for both preliminary and final allocations
        # even on the 256 KiB configuration.
        init_top = memory_top
        original_body, split = split_image(original_body, relocations, link_map,
                                           image_segment, memory_top=memory_top,
                                           init_top=init_top, runtime_top=in_place)
    payload = compress(original_body)
    if source_offset < RING_BYTES or source_offset + len(payload) > 65520:
        raise ValueError("compressed source and history ring exceed one owned segment")
    if RELOCATION_OFFSET + len(relocations) > BRIDGE_STACK_BOTTOM:
        raise ValueError('relocation table overlaps the live bridge stack')
    scratch_extent = source_offset + len(payload)
    if bridge_in_allocation:
        scratch_extent += len(relocations)
    layout = plan_layout(header, original_body, relocations,
                         image_segment=image_segment, load_segment=load_segment,
                         file_segment=file_segment, scratch_segment=scratch_segment,
                         source_extent=scratch_extent,
                         bridge_in_allocation=bridge_in_allocation,
                         memory_top=memory_top)
    if split:
        for name in ('bridge', 'scratch', 'image'):
            start, end = layout['ranges'][name]
            if start < split['init_stack'][1] and split['init'][0] < end:
                raise ValueError('high INIT overlaps live ' + name)
    # In-place mode does not need the relocation/copy trampoline's padding.
    # Keep a paragraph-aligned code prefix and check the actual assembled
    # extent below. This changes neither the decoder nor its owned ranges.
    payload_offset = 0x280 if in_place else 0x400
    # Keep the history ring inside the 65520-byte DOS carrier extent.  The
    # The current 2700h low-staging allocation ends at 36ff0h.  M14 adds
    # resident write code to the linked image; move the 4 KiB history ring by
    # 40h, leaving 0B0h below that ownership end and retaining the same
    # one-segment/bootstrap-stack separation.
    ring_offset = 0xEF40 if in_place else 0
    bridge_stack_segment = (scratch_segment if in_place else
                            (load_segment if bridge_in_allocation else file_segment))
    bridge_stack_sp = 0x7F00 if in_place else 0xFF00
    if in_place and payload_offset + len(payload) + len(relocations) > ring_offset:
        raise ValueError('low staging carrier has no room for its history ring')
    definitions = {
        "M13_LOAD_SEG": load_segment,
        "M13_IMAGE_SEG": image_segment,
        "M13_ZERO_SEG": image_segment + (len(original_body) >> 4),
        "M13_ZERO_OFF": len(original_body) & 15,
        "M13_ZERO_BYTES": layout['zero_bytes'],
        "M13_FILE_SEG": file_segment,
        "M13_SCRATCH_SEG": scratch_segment,
        "M13_PAYLOAD_OFFSET": payload_offset,
        "M13_PAYLOAD_SIZE": len(payload),
        "M13_DATA_SIZE": len(payload),
        "M13_RELOC_INPUT_OFFSET": payload_offset + len(payload),
        "M13_RELOC_SOURCE_OFFSET": (payload_offset + len(payload)
                                     if in_place else
                                     (source_offset + len(payload)
                                      if bridge_in_allocation else RELOCATION_OFFSET)),
        "M13_RELOC_COUNT": len(relocations) // 4,
        "M13_OUTPUT_SIZE": len(original_body),
        "M13_OUTPUT_LO": len(original_body) & 0xFFFF,
        "M13_OUTPUT_HI": len(original_body) >> 16,
        # In-place mode leaves the compressed payload at its carrier offset;
        # the ordinary mode copies it to the separately owned scratch offset.
        "M13_SOURCE_OFFSET": payload_offset if in_place else source_offset,
        "M13_ORIG_SS": header[7],
        "M13_ORIG_SP": header[8],
        "M13_ORIG_CS": header[11],
        "M13_ORIG_IP": header[10],
        "M13_SPLIT_INIT": int(split is not None),
        "M13_IN_PLACE": int(in_place),
        "M13_BRIDGE_IN_ALLOCATION": int(bridge_in_allocation),
        "M13_RING_OFFSET": ring_offset,
        "M13_BRIDGE_STACK_SEG": bridge_stack_segment,
        "M13_BRIDGE_STACK_SP": bridge_stack_sp,
    }
    if split:
        definitions.update({
            'M13_INIT_SOURCE_SEG': split['init_source'][0] // 16,
            'M13_INIT_DEST_SEG': split['init'][0] // 16,
            'M13_INIT_BYTES': split['init'][1] - split['init'][0],
            'M13_INIT_ZERO_BYTES': split['init_stack'][1] - split['init'][1],
            'M13_INIT_STACK_SEG': split['init_stack'][0] // 16,
            'M13_HMA_SOURCE_SEG': split['hma_source'][0] // 16,
            'M13_HMA_DEST_SEG': split['resident_text'][0] // 16,
            'M13_HMA_BYTES': split['resident_text'][1] - split['resident_text'][0],
        })
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="m13-carrier-", dir=output.parent) as temporary:
        bridge_bytes = assemble_bridge(bridge, definitions, Path(temporary) / "bridge.bin")
    if len(bridge_bytes) > payload_offset:
        raise ValueError("M13 bridge exceeds its carrier prefix")
    body = bridge_bytes + bytes(payload_offset - len(bridge_bytes)) + payload + relocations
    if in_place and (-len(body) & 15) < 4:
        # The loader pushes its FAR frame below the rounded entry SP before
        # the bridge reads relocations. A 0..3-byte alignment tail cannot
        # contain that frame: reserve one more paragraph through file bytes.
        # Keep already-safe carrier bytes and the fixed ownership limit intact.
        body += bytes(4)
    if len(body) + 32 > MAX_CARRIER_FILE:
        raise ValueError("M13 carrier exceeds the M08 bounded file extent")
    carrier_allocation = ((len(body) + 15) // 16) * 16
    if in_place:
        # Stage-2 writes its temporary far-return frame below the MZ stack
        # pointer before entering the bridge. The low carrier cannot use the
        # historical 0400h stack value: that frame would overwrite the
        # transformed body. Put the frame in the rounded zero-filled tail
        # immediately after the body and keep it below the history ring.
        if carrier_allocation < 256 or carrier_allocation + 4 > ring_offset:
            raise ValueError('low staging carrier has no disjoint bootstrap stack')
        carrier_stack_pointer = carrier_allocation
    else:
        carrier_stack_pointer = 1024
    pages = (len(body) + 32 + 511) // 512
    last = (len(body) + 32) % 512
    # The DOS header has fourteen words (28 bytes), while cparhdr=2 declares
    # a 32-byte header.  Keep the declared header extent and the actual body
    # origin identical by retaining the four reserved bytes explicitly.
    carrier_header = struct.pack(
        "<14H", 0x5A4D, last, pages, 0, 2, 0, 0, 0, carrier_stack_pointer, 0, 0, 0, 28, 0
    ) + b"\0" * 4
    carrier = carrier_header + body
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    output.write_bytes(carrier)
    return {
        "format": "dos-mz-zero-relocation-m13-carrier",
        "size": len(carrier),
        "sha256": sha256(carrier),
        "body_size": len(original_body),
        "body_sha256": sha256(original_body),
        "linked_body_sha256": sha256(linked_body),
        "split": split,
        "payload_size": len(payload),
        "carrier_allocation": carrier_allocation,
        "carrier_stack_segment": 0,
        "carrier_stack_pointer": carrier_stack_pointer,
        "relocation_count": len(relocations) // 4,
        "bridge_size": len(bridge_bytes),
        "payload_offset": payload_offset,
        "source_offset": source_offset,
        "relocation_source_segment": file_segment,
        "relocation_source_offset": definitions["M13_RELOC_SOURCE_OFFSET"],
        "definitions": definitions,
        "layout": layout,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--bridge", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    # One fixed low-staging envelope is valid on every supported VA memory
    # size.  Override explicitly only for a matched legacy carrier build.
    parser.add_argument("--load-segment", type=lambda value: int(value, 0), default=0x2700)
    parser.add_argument("--image-segment", type=lambda value: int(value, 0), default=0x1000)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--map", type=Path)
    parser.add_argument("--file-segment", type=lambda value: int(value, 0), default=0x2700)
    parser.add_argument("--scratch-segment", type=lambda value: int(value, 0), default=0x3700)
    parser.add_argument("--source-offset", type=lambda value: int(value, 0), default=4096)
    parser.add_argument("--memory-top", type=lambda value: int(value, 0), default=0xA0000)
    parser.add_argument("--no-split", action="store_true",
                        help="keep the linked INIT domain in the resident image")
    parser.add_argument("--bridge-in-allocation", action="store_true",
                        help="run the bridge from the transformed allocation instead of the file segment")
    args = parser.parse_args()
    result = build(args.kernel, args.bridge, args.output, load_segment=args.load_segment,
                   file_segment=args.file_segment, scratch_segment=args.scratch_segment,
                   source_offset=args.source_offset, image_segment=args.image_segment, link_map=args.map,
                   memory_top=args.memory_top, split_init=not args.no_split,
                   bridge_in_allocation=args.bridge_in_allocation)
    if args.manifest:
        args.manifest.write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print("M13_COMPRESSED_CARRIER_PASS")
    print("M13_CARRIER_SIZE=" + str(result["size"]))
    print("M13_CARRIER_SHA256=" + result["sha256"])
    print("M13_ORIGINAL_BODY_SIZE=" + str(result["body_size"]))
    print("M13_PAYLOAD_SIZE=" + str(result["payload_size"]))


if __name__ == "__main__":
    main()
