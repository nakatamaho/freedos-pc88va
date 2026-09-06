#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Add the deterministic, unallocated M12 read fixture to public media."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/m05"))
from build_media import build_d88  # noqa: E402

SECTOR_BYTES = 1024
FIXTURE_LBAS = (200, 201)

def identity(data: bytes) -> dict:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def pattern(lba: int) -> bytes:
    return bytes((lba * 17 + offset * 29 + 3) & 0xff for offset in range(SECTOR_BYTES))

def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) == 2 else None
    if output is None:
        print("usage: build_media.py OUTPUT", file=sys.stderr)
        return 2
    raw_path = output / "raw_media.artifact"
    d88_path = output / "d88_media.artifact"
    manifest_path = output / "rebuilt-manifest.json"
    raw = bytearray(raw_path.read_bytes())
    spec = json.loads((ROOT / "config/m05/media.json").read_text(encoding="utf-8"))
    occupied = set()
    composition = json.loads(manifest_path.read_text(encoding="utf-8"))["composition"]
    first_data = 11
    for record in composition["allocations"]:
        for cluster in record["clusters"]:
            occupied.add(first_data + cluster - 2)
    if any(lba in occupied for lba in FIXTURE_LBAS):
        raise ValueError("M12 fixture overlaps an accepted payload or loader extent")
    sectors = {}
    for lba in FIXTURE_LBAS:
        data = pattern(lba)
        start = lba * SECTOR_BYTES
        raw[start:start + SECTOR_BYTES] = data
        sectors[str(lba)] = identity(data)
    d88 = build_d88(spec, bytes(raw))
    raw_path.write_bytes(raw)
    d88_path.write_bytes(d88)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["m12_fixture"] = {
        "sector_bytes": SECTOR_BYTES,
        "lbas": list(FIXTURE_LBAS),
        "sectors": sectors,
        "read_only": True,
        "pattern": "(lba * 17 + byte_offset * 29 + 3) modulo 256",
    }
    manifest["artifacts"]["raw_media"] = identity(bytes(raw))
    manifest["artifacts"]["d88_media"] = identity(d88)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (output / "m12-fixture.json").write_text(json.dumps(manifest["m12_fixture"], sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("M12 deterministic unallocated read fixture composed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
