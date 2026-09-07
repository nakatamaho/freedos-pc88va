# M05 Deterministic Candidate Media Image

M05 turns the provisional M04 media geometry into a public, reproducible FAT12
logical image and a deterministic D88 container. It is a construction and
inspection milestone. It does not establish that PC-88VA firmware accepts the
medium, loads the first sector, or executes any byte in it.

The normative machine-readable inputs are
[`config/m05/media.json`](../../config/m05/media.json) and its schema. Generated
images and extracted files are ignored under `qa/results/m05/`; only the
reviewed textual golden manifest is committed.

## Geometry and filesystem layout

The M04 candidate geometry is consumed unchanged:

| property | value |
| --- | ---: |
| encoding | MFM |
| bytes per sector | 1,024 |
| sectors per track | 8 |
| heads | 2 |
| cylinders | 80 |
| physical sector ID base | 1 |
| total sectors | 1,280 |
| total bytes | 1,310,720 |

The builder recomputes `80 * 2 * 8 = 1,280` sectors and
`1,280 * 1,024 = 1,310,720` bytes. Logical sectors use:

```text
lba = ((cylinder * 2) + head) * 8 + (sector_id - 1)
```

Every LBA is round-tripped through the inverse mapping. The FAT12 regions are:

| region | LBA range | sectors |
| --- | ---: | ---: |
| reserved/placeholder boot record | 0 | 1 |
| FAT 1 | 1-2 | 2 |
| FAT 2 | 3-4 | 2 |
| root directory | 5-10 | 6 |
| data | 11-1279 | 1,269 |

There is one sector per cluster, two FAT copies, 192 root entries, and media
descriptor `0xFE`. Both FAT copies must be identical. Files are allocated in
the declared payload order using contiguous clusters, while every unallocated
FAT entry and data byte is zero. The independent inspector rejects loops,
cross-links, invalid markers, size/chain disagreements, nonzero unused space,
and extracted payload hash mismatches.

## Placeholder boot record

M04 did not establish a firmware signature, checksum, accepted first-stage
layout, or initial load extent. M05 therefore writes no `0x55AA` signature at
offset 510 or 1022 and makes no bootability claim.

The first three bytes are `EB FE 90`: an x86 short jump to itself followed by
an unreachable NOP. This fail-closed placeholder does not call firmware or
touch I/O. The record contains only the FAT12 descriptive fields declared in
the M05 specification, the fixed OEM identity `FDPC88VA`, fixed volume label
`PC88VA-M05`, fixed serial bytes, and zeroes for all unassigned bytes. The
extended-BPB marker describes the selected FAT representation; it is not a
PC-88VA firmware acceptance marker.

M07 experiments must use separately recorded variants. They must not mutate or
silently reinterpret the M05 golden image contract.

## Deterministic payload policy

M05 selects artifacts by the accepted M02 logical role and namespaced path,
never from an ambient host directory:

| DOS name | M02 role | namespace | use in M05 |
| --- | --- | --- | --- |
| `KERNEL.SYS` | `kernel` | `fdkernel` | NEC98 reference used only for FAT placement and extraction validation |
| `COMMAND.COM` | `command-interpreter` | `freecom` | accepted Japanese FreeCOM reference payload |
| `COUNTRY.SYS` | `standalone-country-driver` | `fdos-country` | accepted standalone Country payload |

The separate fdkernel-internal `COUNTRY.SYS` is not used. The accepted NEC98
kernel is not a PC-88VA kernel and cannot support a VA execution claim. M06 is
responsible for the first compile-only PC-88VA target.

Directory names are lossless uppercase DOS 8.3 ASCII. Each file's FAT date and
time is derived in UTC from its accepted M02 `source_date_epoch`, with the FAT
two-second resolution applied by truncation. Input mtimes and the current clock
are never read.

## D88 subset and provenance

The D88 layout implemented here was reviewed from the public VAEG repository
at commit `2a6c3944bab1fb691261fa2f0950dc4a2faeab8c`, specifically
`fdd/d88head.h`, `fdd/fdd_d88.c`, and `fdd/newdisk.c` in
<https://github.com/nakatamaho/vaeg.git>. No VAEG implementation code or
private D88 bytes are copied.

The independent M05 implementation uses the 688-byte D88 header, 164
little-endian track offsets, and 16-byte sector records. It populates exactly
160 cylinder/head tracks in cylinder-major order, each with sector IDs 1-8,
1,024-byte payloads, and size code `N=3`. The disk type is `0x20`; write
protection, deleted-data, error/status, density-marker, and RPM fields are set
explicitly to zero under this minimal contract. The declared D88 size is
1,331,888 bytes.

The inspector rejects malformed offsets, hidden or duplicate sectors,
incorrect CHRN values, inconsistent lengths, nonzero error/deleted flags, and
trailing data. Extracting all D88 sectors must reproduce the raw image byte for
byte.

## Reproducibility and acceptance boundary

`make m05-build` creates two independent result trees. `make m05-compare`
compares the complete trees byte-for-byte, including images, extracted payloads,
and canonical JSON. `make m05-verify` reruns the independent inspection and
compares the result with the committed textual golden. Canonical JSON contains
no execution time, hostname, username, absolute path, host architecture, or
private identity.

The following M04 facts remain unknown and are not synthesized by M05:

- firmware boot acceptance rules and any required signature or checksum;
- whether firmware initially loads exactly one 1,024-byte sector;
- entry registers, flags, stack, and interrupt state;
- boot-drive identity convention;
- a common firmware disk-service entry point;
- PC-88VA kernel load address, entry point, and handoff state.

M06 may consume the reproducible filesystem role and documented build/memory
assumptions for a compile-only platform target. M07 must determine firmware
acceptance and execution conditions using explicit emulator evidence. M08
remains dependent on a disk-read ABI and kernel placement/handoff contract.

No private manual, ROM, PC-Engine D88 image, or M04 private-analysis result is
an input to M05.
