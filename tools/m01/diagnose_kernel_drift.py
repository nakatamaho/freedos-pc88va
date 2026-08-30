#!/usr/bin/env python3
"""Compare two flat DOS kernel binaries without external binary tools."""

import argparse
import json
import re
import sys
from pathlib import Path


MZ_FIELDS = {
    "bytes_in_last_block": (2, 2),
    "blocks_in_file": (4, 2),
    "relocations": (6, 2),
    "header_paragraphs": (8, 2),
    "relocation_table_offset": (24, 2),
    "overlay_number": (26, 2),
    "new_header_offset": (60, 4),
}


def sha256_bytes(data):
    import hashlib

    return hashlib.sha256(data).hexdigest()


def contiguous_ranges(left, right):
    ranges = []
    start = None
    for offset in range(max(len(left), len(right))):
        differs = offset >= len(left) or offset >= len(right) or left[offset] != right[offset]
        if differs and start is None:
            start = offset
        if not differs and start is not None:
            ranges.append((start, offset))
            start = None
    if start is not None:
        ranges.append((start, max(len(left), len(right))))
    return ranges


def hex_window(data, start, end, context):
    window_start = max(0, start - context)
    window_end = min(len(data), end + context)
    return {
        "offset": window_start,
        "length": window_end - window_start,
        "hex": data[window_start:window_end].hex(),
    }


def printable_window(data, start, end, context):
    window_start = max(0, start - context)
    window_end = min(len(data), end + context)
    rendered = "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in data[window_start:window_end])
    return {
        "offset": window_start,
        "length": window_end - window_start,
        "text": rendered,
    }


def mz_fields(data):
    if len(data) < 2 or data[:2] != b"MZ":
        return None
    result = {}
    for name, (offset, width) in MZ_FIELDS.items():
        if offset + width <= len(data):
            result[name] = int.from_bytes(data[offset:offset + width], "little")
    return result


def strings(data):
    values = []
    match = bytearray()
    match_start = 0
    for offset, byte in enumerate(data + b"\0"):
        if 32 <= byte <= 126:
            if not match:
                match_start = offset
            match.append(byte)
        elif len(match) >= 4:
            values.append((match_start, match.decode("ascii")))
            match.clear()
        else:
            match.clear()
    return values


def string_candidates(data):
    patterns = {
        "date": re.compile(r"(?:19|20)\d\d[-/.]\d\d[-/.]\d\d|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)", re.I),
        "time": re.compile(r"\b\d\d:\d\d(?::\d\d)?\b"),
        "path": re.compile(r"(?:[A-Za-z]:[\\/]|[/\\])|\b(?:src|build|tmp|home|workspace)\b", re.I),
        "version": re.compile(r"\b(?:version|ver|release|v\d|freecom|freedos|kernel)\b", re.I),
        "compiler": re.compile(r"\b(?:watcom|open watcom|compiler|linker|assembler|wlink|wcc)\b", re.I),
    }
    result = {name: [] for name in patterns}
    for offset, value in strings(data):
        for name, pattern in patterns.items():
            if pattern.search(value):
                result[name].append({"offset": offset, "text": value})
    return result


def compare_mz(left, right):
    left_fields = mz_fields(left)
    right_fields = mz_fields(right)
    if left_fields is None and right_fields is None:
        return {"present": False, "differences": {}}
    differences = {}
    for name in sorted(set((left_fields or {})) | set((right_fields or {}))):
        if (left_fields or {}).get(name) != (right_fields or {}).get(name):
            differences[name] = {
                "left": (left_fields or {}).get(name),
                "right": (right_fields or {}).get(name),
            }
    return {
        "present": True,
        "left": left_fields,
        "right": right_fields,
        "differences": differences,
    }


def load(path):
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise ValueError("input is not a regular non-symlink file: " + str(path))
    return path.read_bytes()


def one_input(data):
    return {"size": len(data), "sha256": sha256_bytes(data)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("left")
    parser.add_argument("right")
    parser.add_argument("--left-label", default="accepted")
    parser.add_argument("--right-label", default="fresh")
    parser.add_argument("--left-alias")
    parser.add_argument("--right-alias")
    parser.add_argument("--output", required=True)
    parser.add_argument("--context", type=int, default=16)
    args = parser.parse_args()
    if args.context < 0 or args.context > 256:
        parser.error("--context must be between 0 and 256")
    try:
        left = load(args.left)
        right = load(args.right)
        left_alias = load(args.left_alias) if args.left_alias else None
        right_alias = load(args.right_alias) if args.right_alias else None
    except (OSError, ValueError) as exc:
        print("error: " + str(exc), file=sys.stderr)
        return 2

    ranges = contiguous_ranges(left, right)
    entries = []
    for start, end in ranges:
        entries.append({
            "start": start,
            "end_exclusive": end,
            "length": end - start,
            "left_hex_window": hex_window(left, start, end, args.context),
            "right_hex_window": hex_window(right, start, end, args.context),
            "left_printable_window": printable_window(left, start, end, args.context),
            "right_printable_window": printable_window(right, start, end, args.context),
        })
    report = {
        "schema_version": 1,
        "left_label": args.left_label,
        "right_label": args.right_label,
        "left": one_input(left),
        "right": one_input(right),
        "aliases": {
            "left_internal_equal": None if left_alias is None else left == left_alias,
            "right_internal_equal": None if right_alias is None else right == right_alias,
            "left_alias": None if left_alias is None else one_input(left_alias),
            "right_alias": None if right_alias is None else one_input(right_alias),
        },
        "comparison": {
            "equal": left == right,
            "differing_bytes": sum(
                1
                for offset in range(max(len(left), len(right)))
                if offset >= len(left) or offset >= len(right) or left[offset] != right[offset]
            ),
            "range_count": len(ranges),
            "ranges": entries,
        },
        "mz_header": compare_mz(left, right),
        "string_candidates": {
            args.left_label: string_candidates(left),
            args.right_label: string_candidates(right),
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("kernel comparison: {}".format("equal" if left == right else "different"))
    print("left:  {} bytes {}".format(len(left), sha256_bytes(left)))
    print("right: {} bytes {}".format(len(right), sha256_bytes(right)))
    print("differing bytes: {} across {} ranges".format(report["comparison"]["differing_bytes"], len(ranges)))
    return 0 if left == right else 1


if __name__ == "__main__":
    raise SystemExit(main())
