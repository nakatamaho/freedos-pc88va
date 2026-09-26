# SPDX-License-Identifier: GPL-2.0-or-later
"""Parameterized M08 media composition using unchanged M05 FAT12/D88 logic.

This module has no private-input discovery or execution side effects. A caller
must direct all private-profile output, including returned manifests, to its
ignored persistent evidence sink.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "m05"))
from common import ValidationError, derive_layout, sha256_bytes
from build_media import build_boot_record, build_raw_image, build_d88
from inspect_media import inspect_raw, validate_d88_round_trip


def compose(spec, records, stage2, stage1_factory, signatures):
    """Build stage 2 as a normal file; only its bootstrap extent is fixed.

    KERNEL.SYS remains an independent root entry, found at runtime by the
    stage-2 directory/FAT implementation. No kernel extent is passed to stage 1.
    """
    if [r["dos_name"] for r in records] != ["KERNEL.SYS", "COMMAND.COM", "COUNTRY.SYS"]:
        raise ValidationError("M08 input payload order or set differs")
    if not isinstance(stage2, bytes) or not stage2:
        raise ValidationError("Stage-2 image is empty or not immutable bytes")
    if set(signatures) != {510, 1022} or any(type(v) is not bool for v in signatures.values()):
        raise ValidationError("Signature overlay must explicitly declare both public slots")
    derived = derive_layout(spec)
    if spec["geometry"]["bytes_per_sector"] != 1024 or spec["filesystem"]["sectors_per_cluster"] != 1:
        raise ValidationError("Bootstrap requires the accepted M05 sector/cluster geometry")
    all_records = records + [{"dos_name": "LOADER.BIN", "data": stage2, "size": len(stage2),
                              "sha256": sha256_bytes(stage2),
                              "source_date_epoch": records[0]["source_date_epoch"]}]
    raw, allocation = build_raw_image(spec, derived, all_records)
    _, extracted = inspect_raw(raw, spec, derived, all_records)
    if extracted["LOADER.BIN"] != stage2:
        raise ValidationError("Stage-2 extraction differs")
    chain = allocation["allocations"][-1]["clusters"]
    if chain != list(range(chain[0], chain[0] + len(chain))):
        raise ValidationError("Stage-2 bootstrap extent is not contiguous")
    extent = {"first_lba": derived["first_data_sector"] + chain[0] - 2,
              "sector_count": len(chain), "file_size": len(stage2)}
    boot = bytearray(stage1_factory(extent))
    if len(boot) != 1024 or boot[:3] != b"\xeb\x3c\x90":
        raise ValidationError("Bootstrap sector layout differs")
    if any(boot[3:62]) or boot[510:512] != bytes(2) or boot[1022:] != bytes(2):
        raise ValidationError("Bootstrap overlaps an externally owned boot-record field")
    boot[3:62] = raw[3:62]
    for offset, enabled in signatures.items():
        boot[offset:offset+2] = b"\x55\xaa" if enabled else bytes(2)
    final_raw = bytes(boot) + raw[1024:]
    if final_raw[3:62] != raw[3:62] or final_raw[1024:] != raw[1024:]:
        raise ValidationError("Bootstrap overlay changed BPB or filesystem bytes")
    # The M05 placeholder is intentionally superseded only in the derived M08
    # boot record; restore it in a validation view, never in the experiment.
    view = build_boot_record(spec) + final_raw[1024:]
    _, checked = inspect_raw(view, spec, derived, all_records)
    if checked != extracted:
        raise ValidationError("Overlay changed extracted payloads")
    d88 = build_d88(spec, final_raw)
    validate_d88_round_trip(d88, final_raw, spec, derived)
    return final_raw, d88, {"stage2_extent": extent, "allocations": allocation["allocations"],
                            "raw_sha256": sha256_bytes(final_raw), "d88_sha256": sha256_bytes(d88),
                            "bootstrap_sha256": sha256_bytes(bytes(boot)),
                            "payloads_verified": True, "round_trip_byte_identical": True}
